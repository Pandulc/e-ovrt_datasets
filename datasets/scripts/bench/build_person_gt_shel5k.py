"""GT persona-nivel de SHEL5K desde los XML VOC (doc 66 §B4 del repo docs).

Las clases compuestas del dataset dan el atributo directo:
person_with_helmet -> has_helmet=true; person_no_helmet -> has_helmet=false.
Los labels `person` sueltos (8 en todo el dataset, ruido de anotación) se
descartan. has_vest NO se emite: SHEL5K no lo anota y fabricarlo en false
inventaría violadores CR-02.

Salida (mismo shape que person_gt.json del BENCH):
    datasets/processed/coco/bench/curated/person_gt_shel5k.json

Uso:
    python3 datasets/scripts/bench/build_person_gt_shel5k.py
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = (
    ROOT / "raw/shel5k/9rcv8mm682-4/Safety Helmet Wearing Dataset/Annotations"
)
IMAGES_REL = "datasets/raw/shel5k/9rcv8mm682-4/Safety Helmet Wearing Dataset/Images"
OUT = ROOT / "processed/coco/bench/curated/person_gt_shel5k.json"

_ATTR_BY_CLASS = {"person_with_helmet": True, "person_no_helmet": False}


def records_from_xml(root: ET.Element, file_name: str) -> list[dict]:
    """Extrae los records persona-nivel de un XML VOC de SHEL5K."""
    records = []
    for obj in root.iter("object"):
        name = obj.findtext("name")
        if name not in _ATTR_BY_CLASS:
            continue
        b = obj.find("bndbox")
        bbox = [float(b.findtext(t)) for t in ("xmin", "ymin", "xmax", "ymax")]
        records.append(
            {"person_bbox": bbox, "has_helmet": _ATTR_BY_CLASS[name], "file_name": file_name}
        )
    return records


def main() -> None:
    records = []
    for xml_path in sorted(ANNOTATIONS.iterdir()):
        if xml_path.suffix != ".xml":
            continue
        file_name = f"{IMAGES_REL}/{xml_path.stem}.png"
        records.extend(records_from_xml(ET.parse(xml_path).getroot(), file_name))
    violators = sum(1 for r in records if not r["has_helmet"])
    payload = {
        "source_view": "shel5k VOC (clases compuestas person_with/no_helmet)",
        "matching": "person_bbox xyxy, mismo contrato que person_gt.json del BENCH",
        "note_cr02": "has_vest ausente a propósito: SHEL5K no anota chaleco",
        "total_persons": len(records),
        "violators_cr01": violators,
        "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload))
    print(f"person_gt_shel5k: {len(records)} personas, {violators} violadores CR-01 -> {OUT}")


if __name__ == "__main__":
    main()
