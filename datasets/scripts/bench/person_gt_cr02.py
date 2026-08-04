"""GT de CR-02 a nivel persona desde negativos EXPLICITOS del raw.

`canonical_v2` no lleva la clase `NO-Safety Vest`, asi que `person_gt_bench_obra.json`
trae `has_vest=True` para las 262 personas y lo declara como placeholder. Sin ese campo
la Fase 1 de la Fase D (pre-registro `nucleo/04` §7) no puede puntuar CR-02 y el gate
del §8 queda inaplicable para esa condicion.

La anotacion existe aguas arriba: en el raw de `construction_site_safety` la clase
`NO-Safety Vest` (indice 4) esta marcada por un humano. Este modulo la lee y la hace
pasar por la maquinaria que `build_person_gt.py` ya tiene para `no_vest`
(`build_violation_records` + `build_person_gt_records`, matching center_in_bbox contra
el bbox de la persona).

**D10 (anti-circularidad).** La ausencia NUNCA se infiere por geometria desde cajas
positivas: derivar "sin chaleco" de "no hay caja `vest` dentro de la persona" es la
operacion de E-IND (`spatial_absence`), y usar eso como GT haria circular la
comparacion E-DIR vs E-IND. Fijado por
`datasets/tests/test_person_gt_cr02.py::test_ausencia_de_caja_vest_positiva_NO_marca_violacion`.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/

from bench.build_person_gt import (  # noqa: E402 (after sys.path patch)
    build_person_gt_records,
    build_violation_records,
    person_gt_records_from_coco,
)
from bench.geometry import center_in_bbox  # noqa: E402

# Orden posicional de clases del raw construction_site_safety (v27 data.yaml).
CSS_CLASSES = [
    "Hardhat", "Mask", "NO-Hardhat", "NO-Mask", "NO-Safety Vest",
    "Person", "Safety Cone", "Safety Vest", "machinery", "vehicle",
]
# Solo el negativo de chaleco: CR-01 ya viene resuelto por `bare_head` en canonical_v2
# (D9), y duplicarlo por dos caminos distintos abriria una discrepancia silenciosa.
CSS_NEGATIVES = {"NO-Safety Vest": "no_vest"}


def yolo_line_to_xyxy(line: str, width: int, height: int) -> tuple[int, list[float]]:
    """(class_id, bbox_xyxy en pixeles) desde una linea YOLO normalizada.

    Misma convencion que `parse_yolo` del conversor: centro/ancho/alto normalizados,
    recortado al frame.
    """
    parts = line.split()
    if len(parts) != 5:
        raise ValueError(f"Linea YOLO invalida: {line!r}")
    class_id = int(parts[0])
    x_c, y_c, box_w, box_h = (float(v) for v in parts[1:])
    x1 = (x_c - box_w / 2.0) * width
    y1 = (y_c - box_h / 2.0) * height
    x2 = (x_c + box_w / 2.0) * width
    y2 = (y_c + box_h / 2.0) * height
    x1, y1 = max(0.0, x1), max(0.0, y1)
    x2, y2 = min(float(width), x2), min(float(height), y2)
    return class_id, [x1, y1, x2, y2]


def load_raw_negative_records(
    label_path: Path,
    classes: list[str],
    negatives: dict[str, str],
    width: int,
    height: int,
) -> list[dict]:
    """Registros de violacion desde las clases negativas declaradas de un .txt YOLO.

    Una imagen sin archivo de labels es una imagen sin anotaciones, no un error.
    Las clases POSITIVAS (p.ej. `Safety Vest`) se ignoran por completo: la unica
    fuente de ausencia es el negativo explicito (D10).
    """
    if not Path(label_path).exists():
        return []
    anns = []
    for raw_line in Path(label_path).read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        class_id, bbox = yolo_line_to_xyxy(line, width, height)
        if class_id >= len(classes):
            continue
        name = classes[class_id]
        if name not in negatives:
            continue
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            continue
        anns.append({"source_class": name, "bbox_xyxy": bbox})
    return build_violation_records(anns, negatives)


def _xywh_to_xyxy(bbox: list[float]) -> list[float]:
    x, y, w, h = bbox
    return [x, y, x + w, y + h]


def _area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _containment(inner: list[float], outer: list[float]) -> float:
    """Fraccion del area de `inner` que cae dentro de `outer`."""
    ix0, iy0 = max(inner[0], outer[0]), max(inner[1], outer[1])
    ix1, iy1 = min(inner[2], outer[2]), min(inner[3], outer[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    a = _area(inner)
    return inter / a if a > 0 else 0.0


def assign_negatives_to_persons(
    persons: list[dict],
    violation_recs: list[dict],
) -> tuple[list[list[dict]], int, set[int]]:
    """Atribuye cada violacion `no_vest` a EXACTAMENTE una persona.

    Sin esto, un negativo que cae dentro de dos cuerpos superpuestos marca a los dos:
    en el nucleo curado daba 148 violadores contra 147 negativos, o sea hasta un 10%
    de la clase positiva de CR-02 contaminada con gente que si llevaba chaleco (medido,
    doc 83). El dueno es la persona que mejor CONTIENE al negativo; ante contencion
    total de varias, la de menor area (el marcador se dibuja sobre un torso, no sobre
    la multitud que lo rodea).

    Las violaciones que no son `no_vest` (CR-01, que usa head_region y es mucho mas
    discriminativa) pasan sin tocar.

    Returns:
        (violaciones por persona, cantidad de negativos ambiguos, indices marcados).
    """
    per_person: list[list[dict]] = [[] for _ in persons]
    ambiguos = 0
    marcados: set[int] = set()
    for rec in violation_recs:
        if rec["flag"] != "no_vest":
            for i in range(len(persons)):
                per_person[i].append(rec)
            continue
        candidatos = [i for i, p in enumerate(persons)
                      if center_in_bbox(rec["bbox"], p["bbox_xyxy"])]
        if not candidatos:
            continue
        if len(candidatos) > 1:
            ambiguos += 1
            marcados.update(candidatos)
        dueno = max(
            candidatos,
            key=lambda i: (_containment(rec["bbox"], persons[i]["bbox_xyxy"]),
                           -_area(persons[i]["bbox_xyxy"])),
        )
        per_person[dueno].append(rec)
    return per_person, ambiguos, marcados


def build_person_gt_payload_with_raw_negatives(
    cocos: list[dict],
    labels_by_basename: dict[str, Path],
    classes: list[str],
    negatives: dict[str, str],
) -> dict:
    """Payload person_gt con has_helmet de canonical_v2 y has_vest del negativo raw.

    `labels_by_basename` mapea el basename del `file_name` del COCO al .txt YOLO del
    raw. Una imagen ausente del mapa conserva `has_vest=True` (no se inventa nada).
    """
    records: list[dict] = []
    ambiguos_total = 0
    for coco in cocos:
        cat_map = {c["id"]: c["name"] for c in coco["categories"]}
        by_image: dict[int, list[dict]] = {}
        for ann in coco["annotations"]:
            a = dict(ann)
            a["bbox_xyxy"] = _xywh_to_xyxy(ann["bbox"])
            a["source_class"] = cat_map.get(ann["category_id"], "")
            by_image.setdefault(ann["image_id"], []).append(a)

        for img in coco["images"]:
            img_anns = by_image.get(img["id"], [])
            persons = [a for a in img_anns if a["source_class"] == "person"]
            # CR-01: bare_head == no_helmet explicito en canonical_v2 (garantia D9).
            violations = build_violation_records(img_anns, {"bare_head": "no_helmet"})
            # CR-02: negativo explicito del raw, que canonical_v2 no arrastra.
            basename = Path(img["file_name"]).name
            label_path = labels_by_basename.get(basename)
            if label_path is not None:
                violations += load_raw_negative_records(
                    label_path, classes, negatives, img["width"], img["height"])

            per_person, ambiguos, marcados = assign_negatives_to_persons(persons, violations)
            ambiguos_total += ambiguos
            for i, person in enumerate(persons):
                rec = build_person_gt_records([person], per_person[i])[0]
                rec["image_id"] = img["id"]
                rec["file_name"] = img["file_name"]
                if i in marcados:
                    rec["vest_attribution_ambiguous"] = True
                records.append(rec)

    return {
        "cr02_ambiguous_negatives": ambiguos_total,
        "matching": "center_in_bbox",
        "source_view": "canonical_v2 + negativos explicitos del raw",
        "cr02_source": "explicit_raw_negatives",
        "note_cr01": "has_helmet desde bare_head de canonical_v2 (negativo explicito NO-Hardhat, D9)",
        "note_cr02": (
            "has_vest desde la clase negativa explicita NO-Safety Vest del raw de "
            "construction_site_safety (no llega a canonical_v2). NUNCA inferido por "
            "ausencia de cajas vest positivas: eso seria la operacion de E-IND y haria "
            "circular la comparacion E-DIR vs E-IND (D10)."
        ),
        "total_persons": len(records),
        "violators_cr01": sum(1 for r in records if not r["has_helmet"]),
        "violators_cr02": sum(1 for r in records if not r["has_vest"]),
        "records": records,
    }


def resolve_label_paths(cocos: list[dict], raw_root: Path) -> dict[str, Path]:
    """basename de imagen -> .txt YOLO del raw, buscando en los splits del dataset.

    El `file_name` del COCO ya trae el split ("datasets/raw/.../valid/images/x.jpg"),
    pero se resuelve por busqueda para no acoplarse a esa forma: si el basename no
    aparece en ningun split, la imagen queda fuera del mapa y su has_vest sigue True.
    """
    labels: dict[str, Path] = {}
    for coco in cocos:
        for img in coco["images"]:
            basename = Path(img["file_name"]).name
            stem = Path(basename).stem
            for split in ("valid", "test", "train"):
                candidate = Path(raw_root) / split / "labels" / f"{stem}.txt"
                if candidate.exists():
                    labels[basename] = candidate
                    break
    return labels


def build_bench_obra_payload(coco_paths: list[Path], raw_root: Path) -> dict:
    """Payload del nucleo curado bench_obra con las dos condiciones reales."""
    cocos = [json.loads(Path(p).read_text()) for p in coco_paths]
    labels = resolve_label_paths(cocos, raw_root)
    return build_person_gt_payload_with_raw_negatives(
        cocos, labels, CSS_CLASSES, CSS_NEGATIVES)


def main() -> None:
    p = argparse.ArgumentParser(
        description="GT persona-nivel de bench_obra con CR-02 desde negativos explicitos del raw.")
    p.add_argument("--coco", required=True, type=Path, nargs="+",
                   help="COCOs curados de bench_obra (val + test).")
    p.add_argument("--raw-root", required=True, type=Path,
                   help="Raiz del raw de construction_site_safety (con valid/ test/ train/).")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    payload = build_bench_obra_payload(args.coco, args.raw_root)
    # Control de sanidad visible: si CR-01 se movio, algo se rompio aguas arriba.
    base = [r for coco in (json.loads(Path(c).read_text()) for c in args.coco)
            for r in person_gt_records_from_coco(coco)]
    print(f"Personas: {payload['total_persons']} | CR-01 violadoras: {payload['violators_cr01']} "
          f"(builder vigente: {sum(1 for r in base if not r['has_helmet'])}) "
          f"| CR-02 violadoras: {payload['violators_cr02']}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"GT escrito en {args.out}")


if __name__ == "__main__":
    main()
