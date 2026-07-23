"""Curación bench_obra: sub-splits limpios del BENCH v2, SIN tocar el original.

Auditoría S0 (docs/operacion/63 del repo docs, 2026-07-23): el BENCH v2 del
dataset Roboflow `construction_site_safety` mezcla ~20-25% de imágenes fuera del
dominio obra (selfies COVID con `bare_head` anotado sobre el pelo, PASCAL VOC,
aeropuerto/casino/karting) y trae bboxes `bare_head` sub-pixel. Este script
emite, de forma reproducible:

  processed/coco/bench/curated/construction_site_safety_bench_obra_test.json
  processed/coco/bench/curated/construction_site_safety_bench_obra_val.json
  processed/coco/bench/curated/bench_obra_manifest.json   (deltas vs original)

El COCO original queda INTACTO: la curación es un artefacto derivado aparte, y
el manifiesto declara exactamente qué se excluyó y por qué (imagen por imagen,
conteos por clase antes/después). Registro humano: registry/curation_bench_obra.md.

Uso:
    python3 datasets/scripts/curate/build_bench_obra.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "processed/coco/bench/construction_site_safety_bench.json"
OUT_DIR = ROOT / "processed/coco/bench/curated"

# Grupos FUERA de dominio identificados a ojo en la auditoría S0 (doc 63, tabla
# de prefijos). La regla es por prefijo de basename: reproducible y auditable.
EXCLUDED_PREFIXES = (
    "IMG_",                 # selfies indoor con barbijo COVID
    "Movie-on",             # idem
    "Mask2",                # idem
    "RPReplay",             # idem
    "YouTube_FreeStock",    # calle de Londres, peatones
    "airport_inside",       # interiores sin relación
    "casino",
    "bookstore",
    "Inside-merge",
    "autox",                # karting/racing
    "2008_",                # PASCAL VOC
    "2009_",                # PASCAL VOC
)

# Excluye las bboxes bare_head sub-pixel (2x2.5 px) halladas en S0: GT
# indetectable por diseño que solo distorsiona el AP de la clase.
MIN_BBOX_AREA_PX = 9.0


def _class_counts(coco: dict, annotations: list[dict]) -> dict[str, int]:
    names = {c["id"]: c["name"] for c in coco["categories"]}
    counts = Counter(names[a["category_id"]] for a in annotations)
    return {names[cid]: counts.get(names[cid], 0) for cid in sorted(names)}


def filter_obra(coco: dict) -> tuple[dict, dict, dict]:
    """Filtra el BENCH al dominio obra. Devuelve (obra_test, obra_val, manifest).

    No muta el COCO de entrada.
    """
    excluded_images = []
    kept_images = []
    for im in coco["images"]:
        basename = im["file_name"].split("/")[-1]
        if basename.startswith(EXCLUDED_PREFIXES):
            excluded_images.append({"file_name": im["file_name"], "reason": "domain_prefix"})
        else:
            kept_images.append(im)

    kept_ids = {im["id"] for im in kept_images}
    kept_anns = []
    excluded_min_area = 0
    for a in coco["annotations"]:
        if a["image_id"] not in kept_ids:
            continue
        if a["bbox"][2] * a["bbox"][3] < MIN_BBOX_AREA_PX:
            excluded_min_area += 1
            continue
        kept_anns.append(a)

    def split(fragment: str) -> dict:
        imgs = [im for im in kept_images if fragment in im["file_name"]]
        ids = {im["id"] for im in imgs}
        return {
            "images": imgs,
            "annotations": [a for a in kept_anns if a["image_id"] in ids],
            "categories": coco["categories"],
        }

    obra_test = split("/test/")
    obra_val = split("/valid/")
    manifest = {
        "source": "construction_site_safety_bench.json",
        "audit": "docs/operacion/63 (repo docs, 2026-07-23)",
        "excluded_prefixes": list(EXCLUDED_PREFIXES),
        "min_bbox_area_px": MIN_BBOX_AREA_PX,
        "excluded_images": excluded_images,
        "excluded_annotations_min_area": excluded_min_area,
        "images": {"original": len(coco["images"]),
                   "obra": len(obra_test["images"]) + len(obra_val["images"])},
        "class_counts": {"original": _class_counts(coco, coco["annotations"]),
                         "obra": _class_counts(coco, kept_anns)},
    }
    return obra_test, obra_val, manifest


def main() -> None:
    coco = json.loads(SOURCE.read_text())
    obra_test, obra_val, manifest = filter_obra(coco)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "construction_site_safety_bench_obra_test.json").write_text(
        json.dumps(obra_test))
    (OUT_DIR / "construction_site_safety_bench_obra_val.json").write_text(
        json.dumps(obra_val))
    (OUT_DIR / "bench_obra_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"obra: {manifest['images']['obra']}/{manifest['images']['original']} imgs "
          f"| excluidas {len(manifest['excluded_images'])} por dominio, "
          f"{manifest['excluded_annotations_min_area']} anotaciones sub-área "
          f"| clases obra: {manifest['class_counts']['obra']}")


if __name__ == "__main__":
    main()
