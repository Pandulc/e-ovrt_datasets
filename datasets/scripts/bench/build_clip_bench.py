"""Ensambla y congela el banco de clips: `clip_bench_manifest.json` (doc 75 §1.5).

Cierra el gap de la cadena del doc 54 §5.4: `promote_clip.py` promueve UN clip
y `validate_clip_gt.py` valida GT+manifest, pero nadie armaba la vista
agregada del banco — el análogo de `bench_v3_manifest.json` para video.

Qué produce (en `--bank-dir`, default `datasets/processed/clip_bench/`):
    clip_bench_manifest.json   composición del banco: conteos por escenario
                               (P1–P9 + V*), bloque y estado; positivos vs
                               negativos vs soak (doc 57 G1: negativo de
                               ≥5 min); episodios por condición CR-01/CR-02;
                               duración observada y denominador FAR/hora
                               (SOLO horas soak — doc 57 §3.2 G1; el tiempo
                               negativo corto queda aparte, informativo);
                               doble anotación (doc 58 §B.3); sha256 por GT.
    clip_bench.sha256          formato `sha256sum`: se verifica con
                               `cd <bank-dir> && sha256sum -c clip_bench.sha256`
                               (doc 75 §2.4: el freeze que la herramienta
                               obvia no verifica, no es un freeze).

Gate de estados — el corazón del ensamblado: un banco REPORTABLE exige todas
las filas en `state: gt_ready` (GT con pasada humana en CVAT). `gt_preliminary`
es bring-up (revisión visual asistida) y NO produce números de tesis: sin
`--allow-preliminary` el ensamblado falla; con el flag construye igual pero
estampa `reportable: false` y lista `non_reportable_clips` con su próximo paso.
Cualquier error de consistencia falla cerrado: no se escribe nada.

Consistencia extra sobre validate_clip_gt: `provenance.xml_sha256` de cada GT
debe coincidir con el sha256 del `annotations/<clip_id>.xml` promovido — si el
GT se derivó de OTRO XML que el que está en el banco (la trampa exacta del día
de la corrección CVAT), acá se corta.

Uso (el "día del GT", por cada clip corregido en CVAT y luego una vez al final):
    # 1. exportar el XML corregido a datasets-videos/corrected/<clip_id>.xml
    # 2. python3 datasets/scripts/videogt/derive_clip_gt.py \\
    #        --xml datasets-videos/corrected/<clip_id>.xml \\
    #        --clip-yaml datasets-videos/<clip_id>.clip.yaml \\
    #        --info datasets-videos/clips/<clip_id>.info.json \\
    #        --out datasets-videos/gt/<clip_id>.json
    # 3. python3 datasets/scripts/bench/promote_clip.py --clip-id <clip_id>
    # (todos promovidos, desde la raíz del repo:)
    python3 datasets/scripts/bench/build_clip_bench.py
    cd datasets/processed/clip_bench && sha256sum -c clip_bench.sha256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/ → bench.* importable

from bench.promote_clip import _STATES_NEXT_STEP  # noqa: E402
from bench.validate_clip_gt import validate_manifest  # noqa: E402

DATASETS_ROOT = Path(__file__).resolve().parents[2]  # datasets/
DEFAULT_BANK_DIR = DATASETS_ROOT / "processed/clip_bench"
MANIFEST_JSON = "clip_bench_manifest.json"
CHECKSUMS_FILE = "clip_bench.sha256"
# doc 57 G1: clip "soak" = negativo (`negative: true`) de 5–10 min de obra en
# cumplimiento — el denominador serio de FAR/hora.
SOAK_MIN_MS = 5 * 60 * 1000
P_SCENARIOS = [f"P{i}" for i in range(1, 10)]
CONDITIONS = ["CR-01", "CR-02"]


class ClipBenchError(Exception):
    """El banco no se puede ensamblar: errores de consistencia o de gate."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _committed_artifacts(row: dict) -> list[str]:
    """Rutas (relativas al banco) de los artefactos COMMIT de una fila."""
    return [row[key] for key in ("meta", "preann", "annotations", "gt") if key in row]


def assemble_clip_bench(bank_dir: Path, allow_preliminary: bool = False) -> dict:
    """Arma el dict del manifest del banco. Lanza ClipBenchError si no cierra."""
    manifest_path = bank_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise ClipBenchError([f"no existe {manifest_path} — ¿se promovió algún clip?"])
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    rows = manifest.get("clips") or []
    if not rows:
        raise ClipBenchError(["banco vacío: manifest.yaml sin filas en 'clips'"])

    # 1. Reutiliza la validación existente (schema GT + manifest↔archivos↔sha).
    errors = validate_manifest(manifest, bank_dir)

    # 2. Artefactos COMMIT referenciados deben existir (van al checksums file).
    #    Y los campos que la composición necesita pero validate_manifest no
    #    exige (su FIX 7 solo cubre clip_id/file/gt): sin este chequeo, una
    #    fila sin block/scenario explotaba con KeyError críptico en la
    #    composición en vez de listar qué falta.
    for row in rows:
        cid = row.get("clip_id", "?")
        missing = [key for key in ("block", "scenario") if key not in row]
        if missing:
            errors.append(f"fila del manifest (clip_id={cid}): faltan campos "
                          f"{', '.join(missing)} — requeridos para la "
                          "composición del banco")
        for rel in _committed_artifacts(row):
            if not (bank_dir / rel).exists():
                errors.append(f"{cid}: falta {rel} referenciado por el manifest")

    # 3. Cruce provenance ↔ XML promovido: el GT debe haberse derivado del
    #    MISMO annotations/<clip_id>.xml que vive en el banco.
    gts: dict[str, dict] = {}
    for row in rows:
        cid = row.get("clip_id", "?")
        gt_path = bank_dir / row["gt"] if "gt" in row else None
        if gt_path is None or not gt_path.exists():
            continue
        try:
            gt = json.loads(gt_path.read_text())
        except json.JSONDecodeError as e:
            # Sin esto, un GT roto propagaba JSONDecodeError crudo sin decir
            # qué archivo (mismo espíritu que el FIX 7 de validate_clip_gt).
            errors.append(f"{cid}: GT no parseable ({row['gt']}) — "
                          f"JSON corrupto: {e}")
            continue
        gts[cid] = gt
        declared = (gt.get("provenance") or {}).get("xml_sha256")
        if not declared:
            errors.append(f"{cid}: GT sin provenance.xml_sha256 — no se puede "
                          "verificar de qué XML se derivó (re-derivar con "
                          "derive_clip_gt.py)")
            continue
        ann_rel = row.get("annotations")
        if not ann_rel or not (bank_dir / ann_rel).exists():
            errors.append(f"{cid}: GT presente pero sin annotations/<clip_id>.xml "
                          "en el banco — promover el XML corregido junto al GT")
        elif _sha256_file(bank_dir / ann_rel) != declared:
            errors.append(f"{cid}: provenance.xml_sha256 del GT no coincide con "
                          f"{ann_rel} — el GT se derivó de OTRO XML (re-derivar "
                          "desde el XML corregido vigente y re-promover)")

    # 4. Gate de estados: reportable ⇔ todo gt_ready.
    non_reportable = [row for row in rows
                      if row.get("state", "gt_ready") != "gt_ready"]
    if non_reportable and not allow_preliminary:
        for row in non_reportable:
            state = row.get("state", "gt_ready")
            errors.append(
                f"{row.get('clip_id', '?')}: state '{state}' no es reportable — "
                "un banco congelado exige gt_ready (pasada humana en CVAT); "
                "usar --allow-preliminary solo para un ensamblado de bring-up"
            )
    if errors:
        raise ClipBenchError(errors)

    # 5. Composición.
    clips_out = []
    by_state: dict[str, int] = {}
    by_block: dict[str, int] = {}
    by_scenario: dict[str, int] = {}
    ep_by_condition = {c: 0 for c in CONDITIONS}
    positive = negative = soak_clips = double_annotated = 0
    dur_total = dur_with_gt = dur_negative = dur_soak = 0
    checksums = {"manifest.yaml": _sha256_file(manifest_path)}

    for row in sorted(rows, key=lambda r: r["clip_id"]):
        cid = row["clip_id"]
        state = row.get("state", "gt_ready")
        by_state[state] = by_state.get(state, 0) + 1
        by_block[row["block"]] = by_block.get(row["block"], 0) + 1
        by_scenario[row["scenario"]] = by_scenario.get(row["scenario"], 0) + 1
        dur_total += row.get("duration_ms") or 0
        for rel in _committed_artifacts(row):
            checksums[rel] = _sha256_file(bank_dir / rel)

        entry = {
            "clip_id": cid,
            "block": row["block"],
            "scenario": row["scenario"],
            "level": row.get("level"),
            "state": state,
            "duration_ms": row.get("duration_ms"),
            "media_file": row["file"],
            "media_sha256": row.get("sha256"),
            "gt": row.get("gt"),
            "gt_sha256": None,
            "negative": None,
            "soak": None,
            "n_episodes": None,
            "episodes_by_condition": None,
            "double_annotated": None,
            "annotator": None,
        }
        gt = gts.get(cid)
        if gt is not None:
            gt_duration = gt["duration_ms"]
            is_negative = bool(gt["negative"])
            is_soak = is_negative and gt_duration >= SOAK_MIN_MS
            per_cond = {c: 0 for c in CONDITIONS}
            for ep in gt["episodes"]:
                per_cond[ep["condition_id"]] += 1
                ep_by_condition[ep["condition_id"]] += 1
            entry.update({
                "gt_sha256": checksums[row["gt"]],
                "negative": is_negative,
                "soak": is_soak,
                "n_episodes": len(gt["episodes"]),
                "episodes_by_condition": per_cond,
                "double_annotated": bool(gt["annotation"].get("double_annotated")),
                "annotator": gt["annotation"].get("annotator"),
            })
            dur_with_gt += gt_duration
            if is_negative:
                negative += 1
                dur_negative += gt_duration
            else:
                positive += 1
            if is_soak:
                soak_clips += 1
                dur_soak += gt_duration
            if entry["double_annotated"]:
                double_annotated += 1
        clips_out.append(entry)

    clips_with_gt = len(gts)
    present = sorted(by_scenario)
    return {
        "schema_version": "clip_bench_manifest.v1",
        "reportable": not non_reportable,
        "non_reportable_clips": sorted(
            ({"clip_id": row.get("clip_id", "?"),
              "state": row.get("state", "gt_ready"),
              "next_step": _STATES_NEXT_STEP.get(row.get("state", "gt_ready"), "")}
             for row in non_reportable),
            key=lambda c: c["clip_id"],
        ),
        "clips": clips_out,
        "counts": {
            "clips_total": len(rows),
            "clips_with_gt": clips_with_gt,
            "clips_without_gt": len(rows) - clips_with_gt,
            "by_state": by_state,
            "by_block": by_block,
            "by_scenario": by_scenario,
            "positive_clips": positive,
            "negative_clips": negative,
            "soak_clips": soak_clips,
            "double_annotated_clips": double_annotated,
            "double_annotation_ratio": (
                round(double_annotated / clips_with_gt, 4) if clips_with_gt else None
            ),
        },
        "episodes": {
            "total": sum(ep_by_condition.values()),
            "by_condition": ep_by_condition,
        },
        "duration_ms": {
            "total": dur_total,
            "with_gt": dur_with_gt,
            "negative": dur_negative,
            "soak": dur_soak,
        },
        # doc 57 §3.2 G1: FAR/hora se mide SOLO sobre los clips soak
        # (negativos ≥5 min) — los negativos cortos no son estimador serio del
        # tiempo "aburrido" y NO entran al denominador. Régimen de reporte
        # (doc 59 §6): FP/min sobre la ventana agregada + cota 3/N con 0 FP;
        # FP/hora solo como extrapolación declarada. Sin soak, el denominador
        # queda en 0.0 explícito (no se inventa desde negativos cortos);
        # negative_hours_total es informativo, nunca denominador.
        "far_denominator_hours": round(dur_soak / 3_600_000, 4),
        "far_denominator_basis": "solo clips soak (negativos >= 5 min, doc 57 §3.2 G1)",
        "negative_hours_total": round(dur_negative / 3_600_000, 4),
        "scenario_coverage": {
            "present": present,
            "missing_p_scenarios": [p for p in P_SCENARIOS if p not in present],
        },
        "manifest_yaml_sha256": checksums["manifest.yaml"],
        "checksums": checksums,
        "checksums_file": CHECKSUMS_FILE,
    }


def freeze_payload(manifest: dict) -> str:
    """La ÚNICA serialización congelable: se escribe tal cual (sort_keys para
    bytes deterministas — mismo principio que bench_v3, doc 75 §2.4)."""
    return json.dumps(manifest, sort_keys=True, indent=2) + "\n"


def checksums_text(manifest: dict) -> str:
    """Contenido de clip_bench.sha256 en formato `sha256sum -c`."""
    lines = [f"{sha}  {path}"
             for path, sha in sorted(manifest["checksums"].items())]
    return "\n".join(lines) + "\n"


def write_clip_bench(bank_dir: Path, manifest: dict) -> tuple[Path, Path]:
    json_path = bank_dir / MANIFEST_JSON
    sha_path = bank_dir / CHECKSUMS_FILE
    json_path.write_text(freeze_payload(manifest))
    sha_path.write_text(checksums_text(manifest))
    return json_path, sha_path


def _print_summary(manifest: dict) -> None:
    counts = manifest["counts"]
    print(f"clips: {counts['clips_total']} "
          f"(con GT: {counts['clips_with_gt']}, sin GT: {counts['clips_without_gt']})")
    print(f"por escenario: {counts['by_scenario']}")
    print(f"faltan (P1–P9): {manifest['scenario_coverage']['missing_p_scenarios']}")
    print(f"positivos: {counts['positive_clips']}  negativos: {counts['negative_clips']}"
          f"  soak: {counts['soak_clips']}")
    print(f"episodios: {manifest['episodes']['by_condition']}")
    if counts["soak_clips"]:
        print(f"denominador FAR: {manifest['far_denominator_hours']} h soak "
              f"(tiempo negativo total: {manifest['negative_hours_total']} h — "
              "informativo, no denominador)")
    else:
        print("denominador FAR: 0.0 h — SIN clips soak (doc 57 §3.2 G1): "
              "FAR/hora no computable; el tiempo negativo corto "
              f"({manifest['negative_hours_total']} h) no entra al denominador")
    ratio = counts["double_annotation_ratio"]
    print(f"doble anotación: {counts['double_annotated_clips']} clip(s)"
          f" (ratio {ratio if ratio is not None else 'n/a'}; objetivo ≥0.2, doc 58 §B.3)")
    if manifest["reportable"]:
        print("✓ banco REPORTABLE: todos los clips en gt_ready")
    else:
        print("✗ banco NO reportable — pendientes:")
        for clip in manifest["non_reportable_clips"]:
            print(f"  - {clip['clip_id']} [{clip['state']}]: {clip['next_step']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bank-dir", default=str(DEFAULT_BANK_DIR),
                        help=f"directorio processed del banco (default: {DEFAULT_BANK_DIR})")
    parser.add_argument("--allow-preliminary", action="store_true",
                        help="ensamblar aunque haya clips sin gt_ready "
                             "(marca reportable: false — solo bring-up)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validar y resumir sin escribir nada")
    args = parser.parse_args(argv)
    bank_dir = Path(args.bank_dir)

    try:
        manifest = assemble_clip_bench(bank_dir, allow_preliminary=args.allow_preliminary)
    except ClipBenchError as e:
        for err in e.errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"✗ build_clip_bench: {len(e.errors)} error(es) — no se escribió nada",
              file=sys.stderr)
        return 1

    _print_summary(manifest)
    if args.dry_run:
        print("(dry-run: no se escribió nada)")
        return 0
    json_path, sha_path = write_clip_bench(bank_dir, manifest)
    print(f"escrito: {json_path}")
    print(f"escrito: {sha_path} — verificar con: "
          f"cd {bank_dir} && sha256sum -c {CHECKSUMS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
