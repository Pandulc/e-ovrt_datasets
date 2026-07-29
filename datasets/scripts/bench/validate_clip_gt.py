"""Valida clip_gt.v2 y su cruce con manifest.yaml (spec 43 §5).

Chequea: schema y campos requeridos, episodios dentro de duration_ms,
sin solape de la misma condición (por sujeto en nivel subject),
negative ⇔ sin episodios, y manifest ↔ archivos ↔ sha256 ↔ source_file.

FIX 2 (auditoría 2026-07-11): espejo exacto del contrato de identidad que
exige el evaluador del control-plane (`evaluation/temporal.py`,
`ClipEpisodeV2`) — un episodio `level: scene` sin `source_id`, o
`level: subject` sin `subject_key`, es GT que el evaluador va a rechazar al
cargarlo; este validador lo atrapa acá, antes de llegar al consumidor.

FIX 8 (promote_clip.py, mismo gap de auditoría): manifest ↔ archivos exige
`gt` solo para filas `state: gt_ready` — una fila recién promovida sin GT
todavía (`preannotated`/`corrected`) no debe fallar la validación.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

_REQUIRED_TOP = ["schema_version", "clip_id", "source_file", "block", "scenario",
                 "fps_nominal", "duration_ms", "recording", "negative",
                 "episodes", "sub_threshold_events", "annotation"]
_REQUIRED_EP = ["id", "condition_id", "level", "start_ms", "end_ms",
                "subjects_in_evidence", "notes"]
_BLOCKS = {"A", "B", "C"}
_CONDITIONS = {"CR-01", "CR-02"}
_LEVELS = {"scene", "subject"}
_NEGATIVE_OK_SCENARIOS = {"P5", "V3"}


def validate_gt(gt: dict) -> list[str]:
    """Devuelve la lista de errores del GT (vacía si es válido)."""
    errors = []
    for key in _REQUIRED_TOP:
        if key not in gt:
            errors.append(f"falta campo requerido '{key}'")
    if errors:
        return errors
    cid = gt["clip_id"]
    if gt["schema_version"] != "clip_gt.v2":
        errors.append(f"{cid}: schema_version != clip_gt.v2")
    if gt["block"] not in _BLOCKS:
        errors.append(f"{cid}: block '{gt['block']}' fuera de {sorted(_BLOCKS)}")
    if gt["negative"] != (len(gt["episodes"]) == 0):
        errors.append(f"{cid}: negative debe ser equivalente a 'sin episodios'")

    for ep in gt["episodes"]:
        for key in _REQUIRED_EP:
            if key not in ep:
                errors.append(f"{cid}/{ep.get('id', '?')}: falta '{key}'")
        if ep.get("condition_id") not in _CONDITIONS:
            errors.append(f"{cid}/{ep.get('id')}: condition_id inválido")
        level = ep.get("level")
        if level not in _LEVELS:
            errors.append(f"{cid}/{ep.get('id')}: level '{level}' fuera de {sorted(_LEVELS)}")
        if level == "subject" and not ep.get("subject_label"):
            errors.append(f"{cid}/{ep.get('id')}: level subject sin subject_label")
        if level == "scene" and ep.get("subject_label"):
            errors.append(f"{cid}/{ep.get('id')}: level scene no debe traer subject_label")
        # FIX 2: espejo exacto del validador `_require_key_for_level` del
        # evaluador (control-plane ClipEpisodeV2) — scene exige source_id,
        # subject exige subject_key.
        if level == "scene" and not ep.get("source_id"):
            errors.append(f"{cid}/{ep.get('id')}: level scene sin source_id")
        if level == "subject" and not ep.get("subject_key"):
            errors.append(f"{cid}/{ep.get('id')}: level subject sin subject_key")
        sie = ep.get("subjects_in_evidence")
        if not isinstance(sie, int) or isinstance(sie, bool) or sie < 1:
            errors.append(f"{cid}/{ep.get('id')}: subjects_in_evidence debe ser entero ≥1")
        start, end = ep.get("start_ms", 0), ep.get("end_ms", 0)
        if not (0 <= start < end):
            errors.append(f"{cid}/{ep.get('id')}: start_ms/end_ms inválidos")
        if end > gt["duration_ms"]:
            errors.append(f"{cid}/{ep.get('id')}: end_ms excede duration_ms")

    for i, ev in enumerate(gt.get("sub_threshold_events", [])):
        if ev.get("condition_id") not in _CONDITIONS:
            errors.append(f"{cid}/sub_threshold_events[{i}]: condition_id inválido")
        start, end = ev.get("start_ms", 0), ev.get("end_ms", 0)
        if not (0 <= start < end):
            errors.append(f"{cid}/sub_threshold_events[{i}]: start_ms/end_ms inválidos")
        if end > gt["duration_ms"]:
            errors.append(f"{cid}/sub_threshold_events[{i}]: end_ms excede duration_ms")

    if gt.get("negative") and gt.get("scenario") not in _NEGATIVE_OK_SCENARIOS:
        print(f"[aviso] {cid}: clip negativo con scenario '{gt.get('scenario')}' "
              "(negativos esperados solo en P5/V3) — revisar si es un C2 encubierto "
              "(export sin tracks 'person' por formato/capitalización)")

    # solape de la misma condición (misma persona si level=subject)
    def _key(ep):
        return (ep["condition_id"], ep.get("subject_label")) \
            if ep.get("level") == "subject" else (ep["condition_id"], None)

    groups: dict = {}
    for ep in gt["episodes"]:
        groups.setdefault(_key(ep), []).append(ep)
    for (condition, subject), eps in groups.items():
        eps = sorted(eps, key=lambda e: e["start_ms"])
        for prev, cur in zip(eps, eps[1:]):
            if cur["start_ms"] < prev["end_ms"]:
                who = f" ({subject})" if subject else ""
                errors.append(f"{cid}: solape de {condition}{who}: "
                              f"{prev['id']} y {cur['id']}")
    return errors


def validate_manifest(manifest: dict, base_dir: Path) -> list[str]:
    """Cruza manifest.yaml contra archivos de GT y checksums de media.

    La media puede no estar presente (git-ignored): en ese caso el checksum
    no se verifica y se informa como advertencia por stdout, no como error.

    FIX 8 (promote_clip.py, gap de la auditoría 2026-07-11): un clip recién
    promovido al banco normalmente NO tiene GT todavía (`state:
    preannotated`/`corrected` — es el caso normal de un clip que aún no pasó
    por CVAT + derive_clip_gt.py). Una fila con `state` distinto de
    `gt_ready` no debe fallar la validación por no traer `gt`; sin `state`
    (filas viejas, anteriores a promote_clip.py) se asume `gt_ready` —
    comportamiento previo sin cambios. Una fila `gt_ready` SÍ exige `gt`, y
    cualquier fila que traiga `gt` (tenga o no `state`) se sigue validando
    contra el schema y el cruce de checksums/source_file de siempre.
    """
    errors = []
    for row in manifest.get("clips", []):
        cid = row.get("clip_id", "?")
        state = row.get("state", "gt_ready")
        required = ["clip_id", "file"] + (["gt"] if state in ("gt_ready", "gt_preliminary") else [])
        # FIX 7: una fila sin clip_id/gt/file explotaba con un KeyError
        # críptico en vez de listar qué falta.
        missing = [f for f in required if f not in row]
        if missing:
            errors.append(
                f"fila del manifest (clip_id={cid}): faltan campos {', '.join(missing)}"
            )
            continue
        if "gt" in row:
            gt_path = base_dir / row["gt"]
            if not gt_path.exists():
                errors.append(f"{cid}: falta el GT {row['gt']}")
                continue
            try:
                gt = json.loads(gt_path.read_text())
            except json.JSONDecodeError as e:
                # Mismo espíritu que FIX 7: error claro por fila en vez de
                # propagar json.JSONDecodeError crudo sin decir qué archivo.
                errors.append(f"{cid}: GT no parseable ({row['gt']}) — "
                              f"JSON corrupto: {e}")
                continue
            gt_errors = validate_gt(gt)
            errors.extend(gt_errors)
            if gt.get("clip_id") != cid:
                errors.append(f"{cid}: clip_id del GT no coincide ({gt.get('clip_id')})")
            # FIX 6: cruzar source_file del GT contra el archivo del manifest —
            # un GT promovido sin re-derivar (o apuntando al clip equivocado) no
            # se detectaba antes.
            gt_source_name = Path(gt.get("source_file", "")).name
            manifest_file_name = Path(row["file"]).name
            if gt_source_name != manifest_file_name:
                errors.append(
                    f"{cid}: source_file del GT ({gt.get('source_file')}) no "
                    f"coincide con el archivo del manifest ({row['file']})"
                )
        media = base_dir / row["file"]
        if media.exists():
            digest = hashlib.sha256(media.read_bytes()).hexdigest()
            if digest != row.get("sha256"):
                errors.append(f"{cid}: sha256 no coincide con manifest")
        else:
            print(f"[aviso] {cid}: media ausente ({row['file']}) — checksum no verificado")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt-dir", help="directorio con clip_gt.v2 *.json")
    parser.add_argument("--manifest", help="manifest.yaml del banco")
    parser.add_argument("--base-dir", default=".",
                        help="base para rutas del manifest (default: cwd)")
    args = parser.parse_args(argv)

    errors = []
    if args.gt_dir:
        for path in sorted(Path(args.gt_dir).glob("*.json")):
            errors.extend(validate_gt(json.loads(path.read_text())))
    if args.manifest:
        manifest = yaml.safe_load(Path(args.manifest).read_text())
        errors.extend(validate_manifest(manifest, Path(args.base_dir)))

    for e in errors:
        print(f"ERROR: {e}")
    print(f"{'✗' if errors else '✓'} validate_clip_gt: {len(errors)} error(es)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
