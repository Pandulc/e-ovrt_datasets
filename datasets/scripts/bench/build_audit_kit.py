"""Kit de auditoría visual para Task 4.3 (checkpoint humano del GT del BENCH curado).

Muestrea de forma DETERMINISTA (seed fija) 24 imágenes del núcleo curado bench_obra
(147 imgs), estratificado: ~12 con al menos un violador CR-01 (`has_helmet=False`)
y ~12 solo conformes. Renderiza cada imagen con el GT superpuesto:

  - persona violadora  → caja ROJA,   etiqueta "sin casco"
  - persona conforme   → caja VERDE,  etiqueta "con casco"
  - bare_head anotado  → caja ÁMBAR,  etiqueta "bare_head"

Salida: PNGs numerados (01_… a 24_…) + README.md + sample_manifest.json en
datasets/processed/audit_task43/ (gitignorado — derivado de imágenes raw).

GT auditado: person_gt_bench_obra.json (262 personas / 60 violadores CR-01).
NO usa el person_gt.json histórico (196 imgs, contaminado — ver bench_v3.md).

Uso:
    python3 datasets/scripts/bench/build_audit_kit.py
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

PERSON_GT_PATH = REPO_ROOT / "datasets/processed/coco/bench/curated/person_gt_bench_obra.json"
CURATED_COCOS = [
    REPO_ROOT / "datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_val.json",
    REPO_ROOT / "datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_test.json",
]
DEFAULT_OUT_DIR = REPO_ROOT / "datasets/processed/audit_task43"

COLOR_VIOLATOR = (229, 57, 53)    # rojo — persona sin casco (violador CR-01)
COLOR_COMPLIANT = (67, 160, 71)   # verde — persona con casco
COLOR_BARE_HEAD = (255, 179, 0)   # ámbar — anotación bare_head del COCO curado

_BOX_WIDTH = 3
_LABEL_PAD = 2

README_TEMPLATE = """\
# Kit de auditoría — Task 4.3 (GT del núcleo curado bench_obra)

GT auditado: `datasets/processed/coco/bench/curated/person_gt_bench_obra.json`
(147 imgs curadas, 262 personas, 60 violadores CR-01). Muestra determinista
seed={seed}: {n_violators} imágenes con ≥1 violador + {n_compliant} solo conformes.

Instrucciones (≈15 min):

1. Abrí cada PNG (01–{total:02d}): caja VERDE = persona "con casco" según el GT, caja ROJA = persona "sin casco" (violador CR-01), caja ÁMBAR = anotación `bare_head`.
2. Para cada persona, decidí si el rótulo con/sin casco coincide con lo que se ve en la imagen.
3. Marcá ✓/✗ por imagen en la tabla §4 de `datasets/registry/bench_gt_audit.md` (columna `correcto`) y anotá en `observaciones` cualquier duda o error.
"""


def readme_text(seed: int, n_violators: int, n_compliant: int) -> str:
    """README del kit con los parámetros REALES de generación interpolados.

    Si se regenera con --seed/--n-violators/--n-compliant distintos, el README
    debe describir esa corrida (antes hardcodeaba "seed=43: 12+12" y mentía).
    """
    return README_TEMPLATE.format(seed=seed, n_violators=n_violators,
                                  n_compliant=n_compliant,
                                  total=n_violators + n_compliant)


# ---------------------------------------------------------------- lógica pura

def group_records_by_image(records: list[dict]) -> dict[str, list[dict]]:
    """Agrupa los registros persona del GT por `file_name`."""
    by_img: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_img[rec["file_name"]].append(rec)
    return dict(by_img)


def stratify_images(by_img: dict[str, list[dict]]) -> tuple[list[str], list[str]]:
    """Separa imágenes con ≥1 violador CR-01 de las solo-conformes (listas ordenadas)."""
    violators, compliant = [], []
    for fname in sorted(by_img):
        if any(not r["has_helmet"] for r in by_img[fname]):
            violators.append(fname)
        else:
            compliant.append(fname)
    return violators, compliant


def sample_audit_images(
    violators: list[str],
    compliant: list[str],
    n_violators: int = 12,
    n_compliant: int = 12,
    seed: int = 43,
) -> list[str]:
    """Muestra determinista estratificada; mezcla el orden final (mismo seed)."""
    rng = random.Random(seed)
    picked = rng.sample(violators, min(n_violators, len(violators)))
    picked += rng.sample(compliant, min(n_compliant, len(compliant)))
    rng.shuffle(picked)
    return picked


def summarize_image_gt(records: list[dict]) -> str:
    """Resumen del GT de una imagen, ej: '3 personas: 2 con casco, 1 sin casco'."""
    n = len(records)
    n_with = sum(1 for r in records if r["has_helmet"])
    n_without = n - n_with
    parts = []
    if n_with:
        parts.append(f"{n_with} con casco")
    if n_without:
        parts.append(f"{n_without} sin casco")
    noun = "persona" if n == 1 else "personas"
    return f"{n} {noun}: " + ", ".join(parts)


def person_label(has_helmet: bool) -> str:
    return "con casco" if has_helmet else "sin casco"


def output_name(index: int, file_name: str) -> str:
    """Nombre del PNG numerado: '01_<stem original>.png'."""
    return f"{index:02d}_{Path(file_name).stem}.png"


def coco_bbox_to_xyxy(bbox: list[float]) -> list[float]:
    """COCO [x, y, w, h] → [x1, y1, x2, y2]."""
    x, y, w, h = bbox
    return [x, y, x + w, y + h]


# ---------------------------------------------------------------- render (Pillow)

def _load_font(size: int = 16):
    from PIL import ImageFont

    for candidate in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_box_with_label(draw, bbox: list[float], color: tuple, text: str, font) -> None:
    x1, y1, x2, y2 = bbox
    draw.rectangle([x1, y1, x2, y2], outline=color, width=_BOX_WIDTH)
    tb = draw.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    ty = max(0.0, y1 - th - 2 * _LABEL_PAD)
    draw.rectangle([x1, ty, x1 + tw + 2 * _LABEL_PAD, ty + th + 2 * _LABEL_PAD], fill=color)
    text_color = (0, 0, 0) if color == COLOR_BARE_HEAD else (255, 255, 255)
    draw.text((x1 + _LABEL_PAD, ty + _LABEL_PAD - tb[1]), text, fill=text_color, font=font)


def render_audit_image(image, person_records: list[dict], bare_head_bboxes: list[list[float]]):
    """Devuelve una copia de `image` con el GT dibujado encima (no muta la original)."""
    from PIL import ImageDraw

    out = image.copy()
    draw = ImageDraw.Draw(out)
    font = _load_font()
    for bbox in bare_head_bboxes:
        _draw_box_with_label(draw, bbox, COLOR_BARE_HEAD, "bare_head", font)
    for rec in person_records:
        color = COLOR_COMPLIANT if rec["has_helmet"] else COLOR_VIOLATOR
        _draw_box_with_label(draw, rec["person_bbox"], color, person_label(rec["has_helmet"]), font)
    return out


# ---------------------------------------------------------------- construcción del kit

def _load_bare_heads() -> dict[str, list[list[float]]]:
    """bare_head bboxes (xyxy) por file_name, desde los COCO curados val+test."""
    bare_heads: dict[str, list[list[float]]] = defaultdict(list)
    for coco_path in CURATED_COCOS:
        coco = json.loads(coco_path.read_text())
        cat_ids = {c["id"] for c in coco["categories"] if c["name"] == "bare_head"}
        img_by_id = {img["id"]: img["file_name"] for img in coco["images"]}
        for ann in coco["annotations"]:
            if ann["category_id"] in cat_ids:
                bare_heads[img_by_id[ann["image_id"]]].append(coco_bbox_to_xyxy(ann["bbox"]))
    return dict(bare_heads)


def build_kit(out_dir: Path, n_violators: int, n_compliant: int, seed: int) -> list[dict]:
    from PIL import Image

    gt = json.loads(PERSON_GT_PATH.read_text())
    by_img = group_records_by_image(gt["records"])
    violators, compliant = stratify_images(by_img)
    sampled = sample_audit_images(violators, compliant, n_violators, n_compliant, seed)
    bare_heads = _load_bare_heads()
    violator_set = set(violators)

    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for i, fname in enumerate(sampled, start=1):
        recs = by_img[fname]
        image = Image.open(REPO_ROOT / fname).convert("RGB")
        rendered = render_audit_image(image, recs, bare_heads.get(fname, []))
        png_name = output_name(i, fname)
        rendered.save(out_dir / png_name)
        entries.append({
            "index": i,
            "png": png_name,
            "file_name": fname,
            "split": "valid" if "/valid/" in fname else "test",
            "stratum": "violador" if fname in violator_set else "conforme",
            "n_persons": len(recs),
            "n_violators_cr01": sum(1 for r in recs if not r["has_helmet"]),
            "summary": summarize_image_gt(recs),
        })

    # README con los conteos REALMENTE logrados (pueden capear por universo chico)
    n_viol_actual = sum(1 for e in entries if e["stratum"] == "violador")
    (out_dir / "README.md").write_text(
        readme_text(seed, n_viol_actual, len(entries) - n_viol_actual))
    manifest = {
        "task": "4.3 — auditoría visual del GT curado bench_obra",
        "person_gt": str(PERSON_GT_PATH.relative_to(REPO_ROOT)),
        "seed": seed,
        "n_violators_requested": n_violators,
        "n_compliant_requested": n_compliant,
        "universe": {
            "images_with_persons": len(by_img),
            "images_with_violator": len(violators),
            "images_all_compliant": len(compliant),
        },
        "entries": entries,
    }
    (out_dir / "sample_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--n-violators", type=int, default=12)
    parser.add_argument("--n-compliant", type=int, default=12)
    parser.add_argument("--seed", type=int, default=43)
    args = parser.parse_args()

    entries = build_kit(args.out, args.n_violators, args.n_compliant, args.seed)
    n_viol = sum(1 for e in entries if e["stratum"] == "violador")
    print(f"Kit generado en {args.out} — {len(entries)} imágenes "
          f"({n_viol} con violador CR-01, {len(entries) - n_viol} conformes).\n")
    print("Filas para la tabla §4 de datasets/registry/bench_gt_audit.md:\n")
    for e in entries:
        print(f"| {Path(e['png']).stem} | {e['summary']} | | | |")


if __name__ == "__main__":
    main()
