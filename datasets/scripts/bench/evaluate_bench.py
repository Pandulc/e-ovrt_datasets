"""
Evaluación del BENCH contra detections.jsonl del media-plane.

Uso (par CURADO — el único válido para evaluación):
    python3 datasets/scripts/bench/evaluate_bench.py \
        --detections runs/run_xxx/detections.jsonl runs/run_yyy/detections.jsonl \
        --bench-coco datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_val.json \
        --person-gt datasets/processed/coco/bench/curated/person_gt_bench_obra.json \
        --iou-threshold 0.5

Los COCO curados viven en `datasets/processed/coco/bench/curated/` (val y test
del núcleo bench_obra; el split test se evalúa igual con
`construction_site_safety_bench_obra_test.json`) y se emparejan SIEMPRE con
`person_gt_bench_obra.json`.

ADVERTENCIA: el par histórico `construction_site_safety_bench.json` +
`person_gt.json` (196 imgs, 111 violadoras) está PROHIBIDO para evaluación —
bench contaminado de dominio (ver `datasets/registry/bench_v3.md`).

Produce un resumen de métricas: per-class AP@IoU=0.5, recall CR-01, y conteos.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def load_detections(jsonl_paths: list[Path]) -> dict[str, list[dict]]:
    """Lee uno o más detections.jsonl; devuelve {basename: [detections]}.

    source_id en el JSONL es el basename del archivo de imagen.
    """
    result: dict[str, list[dict]] = {}
    for path in jsonl_paths:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                # source_id es el basename; normalizar por si acaso
                source_id = Path(event["source"]["source_id"]).name
                result.setdefault(source_id, []).extend(event.get("detections", []))
    return result


def load_bench_coco(coco_path: Path) -> tuple[dict, dict, dict]:
    """Carga el COCO del BENCH; devuelve (images_by_basename, gt_by_image_id, cat_by_id).

    file_name en el COCO contiene paths completos; se indexa por basename para
    coincidir con los source_id del pipeline.
    """
    data = json.loads(coco_path.read_text())
    # Indexar por basename para alinear con source_id del pipeline
    images_by_basename = {Path(img["file_name"]).name: img for img in data["images"]}
    gt_by_image_id: dict[int, list[dict]] = defaultdict(list)
    for ann in data["annotations"]:
        gt_by_image_id[ann["image_id"]].append(ann)
    cat_by_id = {cat["id"]: cat["name"] for cat in data["categories"]}
    return images_by_basename, dict(gt_by_image_id), cat_by_id


def load_person_gt(person_gt_path: Path) -> list[dict]:
    """Carga el GT persona-nivel del BENCH."""
    data = json.loads(person_gt_path.read_text())
    return data.get("records", [])


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------

def iou(a: list[float], b: list[float]) -> float:
    """IoU entre dos bboxes [x1,y1,x2,y2]."""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def coco_to_xyxy(bbox_xywh: list[float]) -> list[float]:
    """COCO [x,y,w,h] → [x1,y1,x2,y2]."""
    x, y, w, h = bbox_xywh
    return [x, y, x + w, y + h]


# ---------------------------------------------------------------------------
# Evaluación per-class AP@IoU=0.5 (simplified)
# ---------------------------------------------------------------------------

def evaluate_class(
    class_name: str,
    detections_by_img: dict[str, list[dict]],
    images_by_filename: dict,
    gt_by_image_id: dict,
    cat_by_id: dict,
    iou_threshold: float,
) -> dict:
    """Precision/recall para una clase, usando matching greedy."""
    # Mapear cat_id de la clase
    cat_id = next((k for k, v in cat_by_id.items() if v == class_name), None)
    if cat_id is None:
        return {"class": class_name, "AP50": None, "n_gt": 0, "n_det": 0}

    # Recopilar todas las detecciones de esta clase con su score
    all_dets = []  # (score, image_id, det_bbox_xyxy)
    for filename, img_info in images_by_filename.items():
        dets = detections_by_img.get(filename, [])
        for det in dets:
            if det.get("prompt_id") == class_name or det.get("label", "").lower() in (class_name, class_name.replace("_", " ")):
                all_dets.append((det["confidence"], img_info["id"], det["bbox_xyxy"]))

    # Recopilar todos los GT de esta clase
    gt_matched: dict[int, list[bool]] = {}  # image_id → [matched?]
    n_gt = 0
    for img_id, anns in gt_by_image_id.items():
        gt_for_img = [a for a in anns if a["category_id"] == cat_id]
        if gt_for_img:
            gt_matched[img_id] = [False] * len(gt_for_img)
            n_gt += len(gt_for_img)

    if n_gt == 0:
        return {"class": class_name, "AP50": None, "n_gt": 0, "n_det": len(all_dets)}

    # Ordenar detecciones por score desc
    all_dets.sort(key=lambda x: -x[0])

    tp = []
    fp = []
    for score, img_id, det_bbox in all_dets:
        gt_anns = []
        for ann in gt_by_image_id.get(img_id, []):
            if ann["category_id"] == cat_id:
                gt_anns.append(ann)

        if not gt_anns or img_id not in gt_matched:
            tp.append(0)
            fp.append(1)
            continue

        # Buscar mejor GT por IoU
        best_iou = 0.0
        best_idx = -1
        for i, ann in enumerate(gt_anns):
            gt_bbox = coco_to_xyxy(ann["bbox"])
            iou_val = iou(det_bbox, gt_bbox)
            if iou_val > best_iou:
                best_iou = iou_val
                best_idx = i

        if best_iou >= iou_threshold and not gt_matched[img_id][best_idx]:
            gt_matched[img_id][best_idx] = True
            tp.append(1)
            fp.append(0)
        else:
            tp.append(0)
            fp.append(1)

    # Precisión-recall acumulados
    tp_cum = 0
    fp_cum = 0
    precisions = []
    recalls = []
    for t, f in zip(tp, fp):
        tp_cum += t
        fp_cum += f
        precisions.append(tp_cum / (tp_cum + fp_cum))
        recalls.append(tp_cum / n_gt)

    # AP por interpolación de 11 puntos (VOC estilo)
    ap = 0.0
    for thresh in [r / 10 for r in range(11)]:
        p_at_r = [p for p, r in zip(precisions, recalls) if r >= thresh]
        ap += (max(p_at_r) if p_at_r else 0.0) / 11

    return {
        "class": class_name,
        "AP50": round(ap, 4),
        "n_gt": n_gt,
        "n_det": len(all_dets),
        "n_tp": tp_cum,
        "n_fp": fp_cum,
        "recall": round(tp_cum / n_gt, 4) if n_gt > 0 else 0.0,
        "precision": round(tp_cum / (tp_cum + fp_cum), 4) if (tp_cum + fp_cum) > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# CR-01 recall desde person_gt
# ---------------------------------------------------------------------------

def evaluate_cr01(
    person_gt_records: list[dict],
    detections_by_filename: dict[str, list[dict]],
    images_by_filename: dict,
    iou_threshold: float,
) -> dict:
    """
    Recall CR-01: fracción de personas con has_helmet=False que tienen una detección
    de bare_head (o ausencia de helmet) dentro de su head_region.

    Estrategia E1: detectar bare_head; match si el centro del det cae dentro
    del head_region (tercio superior del person_bbox) o si
    IoU(det, head_region) ≥ threshold — el IoU se computa contra el
    head_region, NO contra el person_bbox completo.

    Nota: las detecciones no se "consumen" al matchear — una misma detección
    de bare_head puede validar a varios violadores con head_regions solapados
    (comportamiento preexistente, documentado a propósito).

    Denominador (fix doc 75 §2.5 — bug del denominador gemelo): solo violadores
    EVALUABLES — en imágenes del bench COCO evaluado (images_by_filename) Y
    cubiertas por el run (con clave en detections_by_filename; load_detections crea
    la clave aunque el evento traiga 0 detecciones). Mismo criterio que
    restrict_gt_to_detections del CLI del media-plane: un violador en una imagen
    que el run no procesó no puede detectarse y deflacionaría el recall; uno fuera
    del bench evaluado está fuera del universo de la evaluación.
    """
    # file_name en person_gt puede ser path completo; alinear por basename
    bench_basenames = {Path(k).name for k in images_by_filename}
    covered_basenames = {Path(k).name for k in detections_by_filename}
    gt_violators_total = sum(1 for r in person_gt_records if not r.get("has_helmet", True))
    cr01_violators = [
        r for r in person_gt_records
        if not r.get("has_helmet", True)
        and Path(r["file_name"]).name in bench_basenames
        and Path(r["file_name"]).name in covered_basenames
    ]
    n_violators = len(cr01_violators)
    if n_violators == 0:
        return {"cr01_recall": None, "n_violators": 0, "n_detected": 0,
                "n_violators_gt_total": gt_violators_total}

    detected = 0
    for rec in cr01_violators:
        fname = Path(rec["file_name"]).name
        dets = detections_by_filename.get(fname, [])
        person_bbox = rec["person_bbox"]
        head = [person_bbox[0], person_bbox[1], person_bbox[2], person_bbox[1] + (person_bbox[3] - person_bbox[1]) / 3]

        for det in dets:
            if det.get("prompt_id") == "bare_head":
                det_bbox = det["bbox_xyxy"]
                cx = (det_bbox[0] + det_bbox[2]) / 2
                cy = (det_bbox[1] + det_bbox[3]) / 2
                if head[0] <= cx <= head[2] and head[1] <= cy <= head[3]:
                    detected += 1
                    break
                if iou(det_bbox, list(head)) >= iou_threshold:
                    detected += 1
                    break

    return {
        "cr01_recall": round(detected / n_violators, 4),
        "n_violators": n_violators,
        "n_detected": detected,
        "n_violators_gt_total": gt_violators_total,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluación BENCH v2")
    parser.add_argument("--detections", nargs="+", required=True, type=Path,
                        help="Uno o más archivos detections.jsonl")
    parser.add_argument("--bench-coco", required=True, type=Path,
                        help="COCO JSON del BENCH curado "
                             "(datasets/processed/coco/bench/curated/*.json). "
                             "El histórico construction_site_safety_bench.json "
                             "está PROHIBIDO para evaluación — ver "
                             "registry/bench_v3.md")
    parser.add_argument("--person-gt", required=True, type=Path,
                        help="GT persona-nivel curado "
                             "(curated/person_gt_bench_obra.json). El histórico "
                             "person_gt.json está PROHIBIDO para evaluación — "
                             "ver registry/bench_v3.md")
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    args = parser.parse_args()

    print(f"Cargando detecciones desde {len(args.detections)} archivo(s)...")
    detections_by_img = load_detections(args.detections)
    print(f"  Imágenes con detecciones: {len(detections_by_img)}")

    print(f"Cargando BENCH COCO: {args.bench_coco}")
    images_by_filename, gt_by_image_id, cat_by_id = load_bench_coco(args.bench_coco)
    print(f"  Imágenes en BENCH: {len(images_by_filename)}")

    print(f"Cargando GT persona-nivel: {args.person_gt}")
    person_gt_records = load_person_gt(args.person_gt)
    print(f"  Registros persona: {len(person_gt_records)}")
    print()

    # Evaluación per-class
    classes = ["person", "helmet", "vest", "bare_head"]
    results = []
    for cls in classes:
        r = evaluate_class(
            cls, detections_by_img, images_by_filename,
            gt_by_image_id, cat_by_id, args.iou_threshold,
        )
        results.append(r)

    print(f"=== Métricas por clase (IoU ≥ {args.iou_threshold}) ===")
    print(f"{'Clase':<12} {'AP@50':>7} {'Recall':>8} {'Precision':>10} {'n_gt':>6} {'n_det':>7}")
    print("-" * 58)
    for r in results:
        ap = f"{r['AP50']:.4f}" if r["AP50"] is not None else "  N/A "
        rec = f"{r.get('recall', 0):.4f}" if r.get("n_gt", 0) > 0 else "  N/A "
        prec = f"{r.get('precision', 0):.4f}" if r.get("n_det", 0) > 0 else "  N/A "
        print(f"{r['class']:<12} {ap:>7} {rec:>8} {prec:>10} {r['n_gt']:>6} {r.get('n_det', 0):>7}")

    valid_aps = [r["AP50"] for r in results if r["AP50"] is not None]
    if valid_aps:
        print(f"\n  mAP@50: {sum(valid_aps)/len(valid_aps):.4f}")

    # Evaluación CR-01
    print()
    print("=== CR-01 recall (E1: bare_head → head_region) ===")
    cr01 = evaluate_cr01(person_gt_records, detections_by_img, images_by_filename, args.iou_threshold)
    excluidas = cr01["n_violators_gt_total"] - cr01["n_violators"]
    if excluidas:
        print(f"  Violadoras del GT excluidas del denominador (fuera del bench o no cubiertas por el run): {excluidas}")
    if cr01["cr01_recall"] is not None:
        print(f"  Recall CR-01: {cr01['cr01_recall']:.4f}  ({cr01['n_detected']}/{cr01['n_violators']} violadoras detectadas)")
    else:
        print("  No hay violadoras CR-01 evaluables (cr01_recall no definido).")


if __name__ == "__main__":
    main()
