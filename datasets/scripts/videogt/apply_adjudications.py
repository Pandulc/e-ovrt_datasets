"""Aplica adjudicaciones humanas de huecos `unknown` sobre el XML corregido (F-GT1).

**Por qué existe.** `derive_clip_gt` trata `unknown` como no evaluable y corta la
corrida de violación (la incertidumbre nunca fabrica una infracción). Cuando el
hueco `unknown` cae en el MEDIO de una violación —con `false` a ambos lados— el
GT declara dos episodios donde el motor de patrones, que ve una persona detectada
de forma continua, sostiene UNA sola alerta: el evaluador matchea el primero y
cuenta el segundo como `missed`, deprimiendo el recall por un artefacto de
anotación (F-GT1, doc 80 §3; misma clase que F-DR9).

**Dónde vive la decisión.** En `clip.yaml`, bajo
`annotation.unknown_adjudications` — NO en el XML. Los XML de
`datasets-videos/corrected/` son artefactos regenerables y gitignoreados: un
parche hecho directamente ahí se pierde **en silencio** en el próximo
`split_cvat_project.py`. El `clip.yaml` se commitea, así que la decisión
sobrevive, viaja al GT (`assemble_clip_gt` propaga el bloque `annotation`) y
queda auditable en el banco.

**El flujo, entonces, es idempotente y re-aplicable:**
    split_cvat_project.py  →  apply_adjudications.py  →  derive_clip_gt.py

Esquema de cada adjudicación (los 6 campos son obligatorios):

    annotation:
      unknown_adjudications:
        - attr: has_helmet        # has_helmet | has_vest
          from_frame: 364         # inclusive, en frames LOCALES del clip
          to_frame: 464           # inclusive
          value: "false"          # true | false — nunca 'unknown'
          decided_by: simonll4    # quién lo decidió mirando el video
          rationale: "sigue sin casco; el unknown era por oclusión de espaldas"

**Lo que el script se niega a hacer**, porque sería fabricar evidencia:
pisar un valor explícito (`true`/`false`) distinto del adjudicado. Solo convierte
`unknown`. Y si el rango no matcheó ninguna caja, corta: una adjudicación firmada
que no se aplicó es peor que ninguna.
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

REQUIRED_FIELDS = ("attr", "from_frame", "to_frame", "value", "decided_by", "rationale")
VALID_VALUES = {"true", "false"}
VALID_ATTRS = {"has_helmet", "has_vest"}


def _validate(adj: dict, idx: int, clip_yaml_path) -> tuple:
    missing = [f for f in REQUIRED_FIELDS
               if f not in adj or adj[f] is None or str(adj[f]).strip() == ""]
    if missing:
        raise ValueError(
            f"{clip_yaml_path}: unknown_adjudications[{idx}] incompleta — faltan "
            f"{', '.join(missing)}. Los 6 campos son obligatorios: una adjudicación "
            "sin firma ni justificación no es auditable."
        )
    value = str(adj["value"]).strip().lower()
    if value not in VALID_VALUES:
        raise ValueError(
            f"{clip_yaml_path}: unknown_adjudications[{idx}]: value "
            f"{adj['value']!r} inválido — debe ser 'true' o 'false' "
            "(adjudicar 'unknown' no resuelve nada)"
        )
    attr = str(adj["attr"]).strip()
    if attr not in VALID_ATTRS:
        raise ValueError(
            f"{clip_yaml_path}: unknown_adjudications[{idx}]: attr {attr!r} "
            f"inválido — debe ser uno de {sorted(VALID_ATTRS)}"
        )
    f0, f1 = int(adj["from_frame"]), int(adj["to_frame"])
    if f1 < f0:
        raise ValueError(
            f"{clip_yaml_path}: unknown_adjudications[{idx}]: rango vacío "
            f"({f0} > {f1}); ambos bordes son inclusivos"
        )
    return attr, f0, f1, value


def apply_adjudications(xml_path, clip_yaml_path, out_path=None) -> dict:
    """Aplica las adjudicaciones de `clip.yaml` sobre `xml_path`. Idempotente."""
    xml_path = Path(xml_path)
    clip_meta = yaml.safe_load(Path(clip_yaml_path).read_text()) or {}
    adjudications = ((clip_meta.get("annotation") or {})
                     .get("unknown_adjudications") or [])

    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    applied, total_changed = [], 0

    for idx, adj in enumerate(adjudications):
        attr, f0, f1, value = _validate(adj, idx, clip_yaml_path)
        changed = already = matched = 0
        conflicts = []
        for track in root.findall("track"):
            for box in track.findall("box"):
                frame = int(box.get("frame"))
                if not f0 <= frame <= f1 or box.get("outside") == "1":
                    continue
                el = next((a for a in box.findall("attribute")
                           if a.get("name") == attr), None)
                if el is None:
                    continue
                matched += 1
                current = (el.text or "").strip().lower()
                if current == "unknown":
                    el.text = value
                    changed += 1
                elif current == value:
                    already += 1
                else:
                    conflicts.append((track.get("id"), frame, current))

        if conflicts:
            sample = ", ".join(f"track {t} f{f}={c!r}" for t, f, c in conflicts[:5])
            raise ValueError(
                f"{clip_yaml_path}: unknown_adjudications[{idx}] ({attr} "
                f"f{f0}-{f1} → {value}) pisaría un valor explícito del anotador "
                f"en {len(conflicts)} caja(s): {sample}. Adjudicar encima de "
                "evidencia humana contraria sería fabricar la violación — "
                "corregí el rango, o corregí la anotación en CVAT."
            )
        if matched == 0:
            raise ValueError(
                f"{clip_yaml_path}: unknown_adjudications[{idx}] ({attr} "
                f"f{f0}-{f1}) no coincidió con ninguna caja del XML "
                f"({xml_path}). ¿Frames en el espacio equivocado, o el rango mal "
                "tipeado? Una adjudicación firmada que no se aplica es peor que "
                "ninguna."
            )

        total_changed += changed
        applied.append({"attr": attr, "from_frame": f0, "to_frame": f1,
                        "value": value, "changed": changed, "already": already,
                        "decided_by": adj["decided_by"]})

    dest = Path(out_path) if out_path else xml_path
    if total_changed or out_path:
        tree.write(str(dest), encoding="utf-8", xml_declaration=True)

    return {"clip_id": clip_meta.get("clip_id"), "xml": str(dest),
            "applied": applied, "total_changed": total_changed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", required=True, help="XML corregido a parchear (in place)")
    parser.add_argument("--clip-yaml", required=True, help="clip.yaml con las adjudicaciones")
    parser.add_argument("--out", default=None, help="escribir acá en vez de in place")
    args = parser.parse_args(argv)

    try:
        r = apply_adjudications(args.xml, args.clip_yaml, args.out)
    except ValueError as e:
        parser.error(str(e))

    if not r["applied"]:
        print(f"  {r['clip_id']}: sin adjudicaciones declaradas — nada que aplicar")
        return 0
    for a in r["applied"]:
        estado = "ya aplicada" if a["changed"] == 0 else f"{a['changed']} cajas → {a['value']}"
        print(f"  {r['clip_id']}: {a['attr']} f{a['from_frame']}-{a['to_frame']} "
              f"→ {a['value']}  ({estado}; firma: {a['decided_by']})")
    print(f"✓ {r['clip_id']}: {r['total_changed']} caja(s) modificada(s) en {r['xml']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
