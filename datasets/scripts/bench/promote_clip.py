"""Promueve un clip del laboratorio (`datasets-videos/`) al banco de clips
(spec 43 §5, layout extendido por el spec del laboratorio §6).

Gap que marcó la auditoría 2026-07-11: sin este script, promover un clip era
copiar 8-15 archivos a mano entre `datasets-videos/` y
`datasets/{raw,processed}/clip_bench/` — inconsistencia garantizada (sha256
desalineado, filas de manifest duplicadas, estado inventado). Este script
hace la copia, verifica el sha256 ANTES de copiar nada, deriva el `state` de
qué artefactos existen de verdad (nunca lo inventa) y hace upsert idempotente
de la fila en `manifest.yaml`.

Uso:
    python3 datasets/scripts/bench/promote_clip.py --clip-id cb_b01_p7 \\
        [--lab-dir datasets-videos] [--state preannotated|corrected|gt_ready]

Layout de origen (laboratorio, `--lab-dir`, default `datasets-videos/`):
    <lab>/clips/<clip_id>.mp4
    <lab>/clips/<clip_id>.info.json
    <lab>/<clip_id>.clip.yaml
    <lab>/preann/<clip_id>.xml
    <lab>/corrected/<clip_id>.xml      (opcional)
    <lab>/gt/<clip_id>.json            (opcional)

Layout de destino (banco):
    <raw-bench-dir>/<clip_id>.mp4                    GIT-IGNORED (Drive)
    <bank-dir>/manifest.yaml                          COMMIT
    <bank-dir>/meta/<clip_id>.clip.yaml               COMMIT
    <bank-dir>/meta/<clip_id>.info.json               COMMIT
    <bank-dir>/preann/<clip_id>.xml                   COMMIT
    <bank-dir>/annotations/<clip_id>.xml              COMMIT (si existe)
    <bank-dir>/gt/<clip_id>.json                      COMMIT (si existe)

Defaults: `--raw-bench-dir datasets/raw/clip_bench/clips`,
`--bank-dir datasets/processed/clip_bench` (ejecutar desde la raíz del repo).

El `state` se deriva de qué artefactos existen — `preannotated` (solo
pre-anotación) → `corrected` (hay XML corregido, sin GT) → `gt_ready` (hay GT
y pasa `validate_gt`). `--state` fuerza un valor explícito sin re-derivarlo.

Para validar el manifest resultante contra los GT y checksums del banco:
    python3 datasets/scripts/bench/validate_clip_gt.py \\
        --manifest datasets/processed/clip_bench/manifest.yaml \\
        --base-dir datasets/processed/clip_bench
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/ → bench.* importable

from bench.validate_clip_gt import validate_gt  # noqa: E402 (after sys.path patch)

DEFAULT_LAB_DIR = "datasets-videos"
DEFAULT_BANK_DIR = "datasets/processed/clip_bench"
DEFAULT_RAW_BENCH_DIR = "datasets/raw/clip_bench/clips"
REQUIRED_CLIP_YAML_FIELDS = ["clip_id", "block", "scenario"]
_STATES_NEXT_STEP = {
    "preannotated": "corregir en CVAT y exportar a corrected/<clip_id>.xml",
    "corrected": "derivar el GT con derive_clip_gt.py hacia gt/<clip_id>.json",
    # gt_preliminary: GT valido pero la correccion NO fue la pasada humana
    # controlada en CVAT (p.ej. revision visual asistida). Sirve para bring-up
    # y pruebas de plataforma; NO para numeros reportables de tesis.
    "gt_preliminary": "reemplazar por la correccion humana controlada en CVAT",
    "gt_ready": "banco completo — correr validate_clip_gt.py contra el manifest",
}


class PromoteClipError(Exception):
    """Artefactos de laboratorio faltantes, inconsistentes o sha256 no verificado."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lab_artifact_paths(lab_dir: Path, clip_id: str) -> dict[str, Path]:
    return {
        "mp4": lab_dir / "clips" / f"{clip_id}.mp4",
        "info": lab_dir / "clips" / f"{clip_id}.info.json",
        "clip_yaml": lab_dir / f"{clip_id}.clip.yaml",
        "preann": lab_dir / "preann" / f"{clip_id}.xml",
        "corrected": lab_dir / "corrected" / f"{clip_id}.xml",
        "gt": lab_dir / "gt" / f"{clip_id}.json",
    }


def _check_required_artifacts(paths: dict[str, Path], clip_id: str) -> None:
    """mp4/info.json/clip.yaml/preann son obligatorios para cualquier promoción.

    corrected/gt son opcionales (determinan el `state`, no bloquean).
    """
    required = ["mp4", "info", "clip_yaml", "preann"]
    missing = [str(paths[key]) for key in required if not paths[key].exists()]
    if missing:
        raise PromoteClipError(
            f"{clip_id}: faltan artefactos del laboratorio requeridos para "
            f"promover — {', '.join(missing)}. No se copió nada."
        )


def _load_clip_yaml(path: Path) -> dict:
    clip_meta = yaml.safe_load(path.read_text())
    if not isinstance(clip_meta, dict):
        raise PromoteClipError(f"{path}: clip.yaml vacío o mal formado (se esperaba un mapeo)")
    missing = [f for f in REQUIRED_CLIP_YAML_FIELDS if f not in clip_meta]
    if missing:
        raise PromoteClipError(
            f"{path}: faltan campos requeridos en clip.yaml: {', '.join(missing)}"
        )
    return clip_meta


def _verify_sha256(clip_id: str, mp4_path: Path, info: dict) -> None:
    expected = info.get("sha256")
    if not expected:
        raise PromoteClipError(f"{clip_id}: info.json no trae 'sha256' — no se puede verificar")
    actual = _sha256_file(mp4_path)
    if actual != expected:
        raise PromoteClipError(
            f"{clip_id}: sha256 no coincide — {mp4_path} tiene {actual}, "
            f"info.json declara {expected}. El clip del laboratorio no es el "
            "que se anotó (¿se re-preparó el clip después de anotar?). No se "
            "copió nada."
        )


def _derive_state(has_corrected: bool, gt_errors: list[str] | None) -> str:
    if gt_errors is not None and not gt_errors:
        return "gt_ready"
    if has_corrected:
        return "corrected"
    return "preannotated"


def promote_clip(clip_id: str, lab_dir: Path, bank_dir: Path, raw_bench_dir: Path,
                  state_override: str | None = None) -> dict:
    """Promueve `clip_id` del laboratorio (`lab_dir`) al banco. Devuelve la fila
    de manifest resultante (ya escrita en `<bank_dir>/manifest.yaml`).
    """
    lab_dir = Path(lab_dir)
    bank_dir = Path(bank_dir)
    raw_bench_dir = Path(raw_bench_dir)

    paths = _lab_artifact_paths(lab_dir, clip_id)
    _check_required_artifacts(paths, clip_id)

    info = json.loads(paths["info"].read_text())
    _verify_sha256(clip_id, paths["mp4"], info)
    clip_meta = _load_clip_yaml(paths["clip_yaml"])
    if clip_meta["clip_id"] != clip_id:
        raise PromoteClipError(
            f"{clip_id}: clip_id de clip.yaml ({clip_meta['clip_id']!r}) no "
            f"coincide con --clip-id ({clip_id!r})"
        )

    has_corrected = paths["corrected"].exists()
    has_gt = paths["gt"].exists()
    gt_errors = None
    if has_gt:
        gt = json.loads(paths["gt"].read_text())
        gt_errors = validate_gt(gt)
        if gt_errors:
            print(f"[aviso] {clip_id}: GT presente pero inválido, no se promueve a "
                  f"gt_ready — {'; '.join(gt_errors)}")

    state = state_override or _derive_state(has_corrected, gt_errors)

    # Copia — recién ahora que el sha256 verificó y los artefactos requeridos
    # existen. Nada se toca si algo de lo anterior falló.
    (bank_dir / "meta").mkdir(parents=True, exist_ok=True)
    (bank_dir / "preann").mkdir(parents=True, exist_ok=True)
    raw_bench_dir.mkdir(parents=True, exist_ok=True)

    raw_mp4_dest = raw_bench_dir / f"{clip_id}.mp4"
    shutil.copy2(paths["mp4"], raw_mp4_dest)
    shutil.copy2(paths["info"], bank_dir / "meta" / f"{clip_id}.info.json")
    shutil.copy2(paths["clip_yaml"], bank_dir / "meta" / f"{clip_id}.clip.yaml")
    shutil.copy2(paths["preann"], bank_dir / "preann" / f"{clip_id}.xml")

    row = {
        "clip_id": clip_id,
        "file": str(Path(_relpath(raw_mp4_dest, bank_dir))),
        "sha256": info["sha256"],
        "fps": info.get("fps"),
        "duration_ms": info.get("duration_ms"),
        "resolution": info.get("resolution"),
        "block": clip_meta["block"],
        "scenario": clip_meta["scenario"],
        "level": clip_meta.get("level", "scene"),
        "state": state,
        "preann": f"preann/{clip_id}.xml",
        "meta": f"meta/{clip_id}.clip.yaml",
    }

    if has_corrected:
        (bank_dir / "annotations").mkdir(parents=True, exist_ok=True)
        shutil.copy2(paths["corrected"], bank_dir / "annotations" / f"{clip_id}.xml")
        row["annotations"] = f"annotations/{clip_id}.xml"

    if has_gt:
        (bank_dir / "gt").mkdir(parents=True, exist_ok=True)
        shutil.copy2(paths["gt"], bank_dir / "gt" / f"{clip_id}.json")
        row["gt"] = f"gt/{clip_id}.json"

    _upsert_manifest(bank_dir / "manifest.yaml", row)
    _print_summary(clip_id, row, has_corrected, has_gt, gt_errors)
    return row


def _relpath(target: Path, start: Path) -> str:
    """Ruta relativa de `target` respecto de `start`, sin exigir que existan
    (`Path.relative_to` sí lo exige; `os.path.relpath` no resuelve symlinks,
    que es justo lo que queremos acá: rutas declarativas para el manifest).
    """
    import os
    return os.path.relpath(target, start=start)


def _upsert_manifest(manifest_path: Path, row: dict) -> dict:
    """Upsert idempotente por `clip_id`: reemplaza la fila si ya existe, la
    agrega si no, y reordena todo por `clip_id` (determinismo del manifest).
    """
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
    else:
        manifest = {}
    clips = [c for c in manifest.get("clips", []) if c.get("clip_id") != row["clip_id"]]
    clips.append(row)
    clips.sort(key=lambda c: c["clip_id"])
    manifest["clips"] = clips
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
    return manifest


def _print_summary(clip_id: str, row: dict, has_corrected: bool, has_gt: bool,
                    gt_errors: list[str] | None) -> None:
    copied = ["mp4", "info.json", "clip.yaml", "preann.xml"]
    if has_corrected:
        copied.append("annotations.xml")
    if has_gt:
        copied.append("gt.json" + (" (inválido, no promovido a gt_ready)" if gt_errors else ""))
    print(f"\n=== {clip_id}: promovido al banco ===")
    print(f"  copiado: {', '.join(copied)}")
    print(f"  state: {row['state']}")
    next_step = _STATES_NEXT_STEP.get(row["state"])
    if next_step:
        print(f"  próximo paso: {next_step}")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--clip-id", required=True, help="id del clip a promover")
    parser.add_argument("--lab-dir", default=DEFAULT_LAB_DIR,
                        help=f"directorio del laboratorio (default: {DEFAULT_LAB_DIR})")
    parser.add_argument("--bank-dir", default=DEFAULT_BANK_DIR,
                        help=f"directorio processed del banco (default: {DEFAULT_BANK_DIR})")
    parser.add_argument("--raw-bench-dir", default=DEFAULT_RAW_BENCH_DIR,
                        help=f"directorio raw del banco, git-ignored (default: {DEFAULT_RAW_BENCH_DIR})")
    parser.add_argument("--state", choices=["preannotated", "corrected", "gt_preliminary", "gt_ready"],
                        default=None, help="override explícito del state (default: derivado)")
    args = parser.parse_args(argv)

    try:
        promote_clip(args.clip_id, Path(args.lab_dir), Path(args.bank_dir),
                     Path(args.raw_bench_dir), state_override=args.state)
    except PromoteClipError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
