"""GT persona-nivel del BENCH desde negativos explícitos (spec §5, anti-circularidad).

NO se infiere ausencia por geometría persona<->helmet: cada registro de violación
proviene de una anotación negativa explícita marcada por un humano.

Flujo de dos pasos:
  1. build_violation_records  — extrae registros de violación de las anotaciones negativas.
  2. build_person_gt_records  — asocia violaciones con personas via IoU (GT per-persona).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/ → bench.geometry importable

from bench.geometry import center_in_bbox, head_region  # noqa: E402 (after sys.path patch)

_FLAG_TO_CONDITION = {"no_helmet": "CR-01", "no_vest": "CR-02"}


def build_violation_records(annotations: list[dict], negatives: dict[str, str]) -> list[dict]:
    """Crea registros de violación desde anotaciones de clase negativa explícita.

    Args:
        annotations: lista de anotaciones con campos 'source_class' y 'bbox_xyxy'.
        negatives: mapeo {nombre_clase_original: 'no_helmet'|'no_vest'}.

    Returns:
        Lista de registros {'bbox', 'flag', 'condition'} — uno por anotación negativa.
    """
    records = []
    for ann in annotations:
        src = ann.get("source_class")
        flag = negatives.get(src)
        if flag is None:
            continue
        records.append({
            "bbox": ann["bbox_xyxy"],
            "flag": flag,
            "condition": _FLAG_TO_CONDITION[flag],
        })
    return records


def build_person_gt_records(
    person_anns: list[dict],
    violation_recs: list[dict],
) -> list[dict]:
    """Construye GT por-persona asignando has_helmet/has_vest desde registros de violación.

    Para CR-01 (no_helmet): el centro del bbox de violación debe caer dentro de head_region(persona).
    Para CR-02 (no_vest):   el centro del bbox de violación debe caer dentro del bbox de la persona.

    Usa center-containment en lugar de IoU porque los bboxes de violation y region de referencia
    tienen áreas muy distintas (ej: bare_head tight vs head_region del tercio superior del cuerpo).

    Anti-circularidad D10: la asignación usa anotaciones negativas EXPLÍCITAS del dataset,
    no el resultado de E1 (detección de helmets positivos).

    Args:
        person_anns: anotaciones de clase 'person' con campo 'bbox_xyxy'.
        violation_recs: salida de build_violation_records para la misma imagen.

    Returns:
        Lista de dicts {'person_bbox', 'has_helmet', 'has_vest'} — uno por persona.
    """
    result = []
    for person in person_anns:
        pbbox = person["bbox_xyxy"]
        head = list(head_region(pbbox))
        has_helmet = True
        has_vest = True
        for rec in violation_recs:
            vbbox = rec["bbox"]
            if rec["flag"] == "no_helmet" and center_in_bbox(vbbox, head):
                has_helmet = False
            elif rec["flag"] == "no_vest" and center_in_bbox(vbbox, pbbox):
                has_vest = False
        result.append({
            "person_bbox": pbbox,
            "has_helmet": has_helmet,
            "has_vest": has_vest,
        })
    return result


def _xywh_to_xyxy(bbox: list[float]) -> list[float]:
    x, y, w, h = bbox
    return [x, y, x + w, y + h]


def person_gt_records_from_coco(coco: dict) -> list[dict]:
    """Records persona-nivel para un COCO canonical_v2.

    En canonical_v2, bare_head proviene SOLO de negativos explícitos (D9), por lo
    que cada bare_head annotation es ya un proxy confiable de no_helmet.
    """
    cat_map = {c["id"]: c["name"] for c in coco["categories"]}

    # Group annotations by image; convert COCO xywh bbox to xyxy
    by_image: dict[int, list[dict]] = {}
    for ann in coco["annotations"]:
        a = dict(ann)
        a["bbox_xyxy"] = _xywh_to_xyxy(ann["bbox"])
        a["source_class"] = cat_map.get(ann["category_id"], "")
        by_image.setdefault(ann["image_id"], []).append(a)

    # In canonical_v2: bare_head == explicit no_helmet (D9 guarantee)
    v2_negatives = {"bare_head": "no_helmet"}

    all_person_gt: list[dict] = []
    for img in coco["images"]:
        img_anns = by_image.get(img["id"], [])
        persons = [a for a in img_anns if a["source_class"] == "person"]
        violations = build_violation_records(img_anns, v2_negatives)
        person_gt = build_person_gt_records(persons, violations)
        for rec in person_gt:
            rec["image_id"] = img["id"]
            rec["file_name"] = img["file_name"]
        all_person_gt.extend(person_gt)
    return all_person_gt


def build_person_gt_payload(cocos: list[dict]) -> dict:
    """Payload person_gt (mismo contrato que el histórico) desde uno o más COCOs.

    Acepta múltiples COCOs porque el núcleo curado de bench_obra vive en dos
    archivos (val + test curados); los records se concatenan y los conteos se
    calculan sobre el total. Los image_id se conservan tal cual vienen de cada
    fuente (la evaluación matchea por basename de file_name, no por id).
    """
    records: list[dict] = []
    for coco in cocos:
        records.extend(person_gt_records_from_coco(coco))

    violators_cr01 = sum(1 for r in records if not r["has_helmet"])
    violators_cr02 = sum(1 for r in records if not r["has_vest"])
    return {
        "matching": "center_in_bbox",
        "source_view": "canonical_v2",
        "note_cr02": "has_vest=True para todos (NO-Safety Vest no es clase canonical_v2; ver raw annotations)",
        "total_persons": len(records),
        "violators_cr01": violators_cr01,
        "violators_cr02": violators_cr02,
        "records": records,
    }


def main() -> None:
    """Construye GT persona-nivel desde canonical_v2 COCO(s) del BENCH.

    CR-02 (has_vest) queda True si no hay anotaciones NO-Safety Vest disponibles en esta vista.
    """
    p = argparse.ArgumentParser(description="Construye GT persona-nivel del BENCH.")
    p.add_argument("--coco", required=True, type=Path, nargs="+",
                   help="Uno o más COCOs canonical_v2 del BENCH (ej: val + test curados de bench_obra)")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    payload = build_person_gt_payload([json.loads(path.read_text()) for path in args.coco])
    print(f"Personas: {payload['total_persons']} | CR-01 violadoras: {payload['violators_cr01']} "
          f"| CR-02 violadoras: {payload['violators_cr02']}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"GT escrito en {args.out}")


if __name__ == "__main__":
    main()
