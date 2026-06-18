"""Arma las vistas por rol desde canonical_v2, respetando contrato, fuga y balance.

Uso:
    python3 datasets/scripts/curate/build_role_views.py \
        --scoring datasets/registry/selection_scoring.csv \
        --min-per-class 150

Para cada dataset seleccionado con canonical_v2 disponible:
  - TRAIN: todos los splits (train/val/test) de datasets con rol TRAIN
  - BENCH: split test (o val como fallback) del dataset con rol BENCH
  - DEMO:  train split de datasets con calidad >= min_demo_quality (para presentación)

Salida: datasets/splits/v2/{train,bench,demo}.txt  (rutas a imágenes, una por línea)
        datasets/splits/v2/manifest.json           (resumen con conteos por clase)
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "processed"
SPLITS_DIR = ROOT / "splits" / "v2"

V2_CLASSES = ("person", "helmet", "vest", "bare_head")


def meets_min_per_class(counts: dict[str, int], minimum: int) -> bool:
    """Verifica que todas las clases v2 superen el mínimo de anotaciones."""
    return all(counts.get(c, 0) >= minimum for c in V2_CLASSES)


def find_leaks(train_ids: set[str], bench_ids: set[str]) -> set[str]:
    return train_ids & bench_ids


def _load_coco_splits(dataset_id: str, splits: list[str]) -> list[dict]:
    base = PROCESSED / "coco" / "canonical_v2" / dataset_id
    result = []
    for sp in splits:
        p = base / f"{sp}.json"
        if p.exists():
            result.append(json.loads(p.read_text()))
    return result


def _image_stems(coco_list: list[dict]) -> set[str]:
    return {Path(img["file_name"]).stem for coco in coco_list for img in coco["images"]}


def _image_paths(coco_list: list[dict]) -> list[str]:
    return [img["file_name"] for coco in coco_list for img in coco["images"]]


def _annotation_counts(coco_list: list[dict]) -> Counter:
    counts: Counter = Counter()
    for coco in coco_list:
        cat_map = {c["id"]: c["name"] for c in coco["categories"]}
        for ann in coco["annotations"]:
            counts[cat_map[ann["category_id"]]] += 1
    return counts


def main() -> None:
    p = argparse.ArgumentParser(description="Genera vistas por rol (TRAIN/BENCH/DEMO) desde canonical_v2.")
    p.add_argument("--scoring", default=str(ROOT / "registry" / "selection_scoring.csv"), type=Path)
    p.add_argument("--min-per-class", type=int, default=150)
    args = p.parse_args()

    with args.scoring.open() as f:
        rows = [r for r in csv.DictReader(f) if r["decision"] == "seleccionado"]

    train_ds = [r["dataset_id"] for r in rows if "TRAIN" in r.get("rol", "")]
    bench_ds = [r["dataset_id"] for r in rows if "BENCH" in r.get("rol", "")]

    # --- TRAIN ---
    train_paths: list[str] = []
    train_ids: set[str] = set()
    train_counts: Counter = Counter()
    missing: list[str] = []

    for ds in train_ds:
        # Exclude BENCH splits from TRAIN to prevent leakage (spec §8.5, D13)
        # BENCH uses val+test, so BENCH datasets only contribute train split to TRAIN
        splits_for_train = ["train"] if ds in bench_ds else ["train", "val", "test"]
        coco = _load_coco_splits(ds, splits_for_train)
        if not coco:
            print(f"[SKIP-TRAIN] {ds}: canonical_v2 not yet available")
            missing.append(ds)
            continue
        ids = _image_stems(coco)
        counts = _annotation_counts(coco)
        train_paths.extend(_image_paths(coco))
        train_ids |= ids
        train_counts += counts
        print(f"[TRAIN] {ds}: {len(ids)} imgs  {dict(counts)}")

    # --- BENCH (val+test when both exist; fallback to whichever is present) ---
    bench_paths: list[str] = []
    bench_ids: set[str] = set()
    bench_counts: Counter = Counter()

    for ds in bench_ds:
        base = PROCESSED / "coco" / "canonical_v2" / ds
        available = [s for s in ["val", "test"] if (base / f"{s}.json").exists()]
        preferred = available if available else ["val"]
        coco = _load_coco_splits(ds, preferred)
        if not coco:
            print(f"[SKIP-BENCH] {ds}: canonical_v2 not yet available")
            missing.append(ds)
            continue
        ids = _image_stems(coco)
        counts = _annotation_counts(coco)
        bench_paths.extend(_image_paths(coco))
        bench_ids |= ids
        bench_counts += counts
        print(f"[BENCH] {ds} ({preferred[0]}): {len(ids)} imgs  {dict(counts)}")

    # --- DEMO: train split of datasets with 0 quality defects ---
    demo_paths: list[str] = []
    demo_ids: set[str] = set()
    demo_counts: Counter = Counter()
    demo_rows = [r for r in rows if float(r.get("calidad_defectos_pct", "99") or "99") == 0]

    for r in demo_rows:
        ds = r["dataset_id"]
        coco = _load_coco_splits(ds, ["train"])
        if not coco:
            continue
        ids = _image_stems(coco)
        counts = _annotation_counts(coco)
        demo_paths.extend(_image_paths(coco))
        demo_ids |= ids
        demo_counts += counts
        print(f"[DEMO] {ds}: {len(ids)} imgs  {dict(counts)}")

    # --- Leakage check ---
    if train_ids and bench_ids:
        leaks = train_ids & bench_ids
        if leaks:
            print(f"ERROR: {len(leaks)} image stems shared TRAIN↔BENCH: {sorted(leaks)[:5]}", file=sys.stderr)
            sys.exit(1)
        print(f"Leakage TRAIN↔BENCH: OK (no shared stems)")

    # --- Balance ---
    if bench_ids:
        ok = meets_min_per_class(dict(bench_counts), args.min_per_class)
        status = "OK" if ok else "INSUFICIENTE"
        print(f"BENCH balance (min={args.min_per_class}): {status}")
        for cls in V2_CLASSES:
            flag = "" if bench_counts.get(cls, 0) >= args.min_per_class else " ⚠"
            print(f"  {cls}: {bench_counts.get(cls, 0)}{flag}")

    # --- Write manifests ---
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    if train_paths:
        (SPLITS_DIR / "train.txt").write_text("\n".join(train_paths) + "\n")
    if bench_paths:
        (SPLITS_DIR / "bench.txt").write_text("\n".join(bench_paths) + "\n")
    if demo_paths:
        (SPLITS_DIR / "demo.txt").write_text("\n".join(demo_paths) + "\n")

    manifest = {
        "train": {"images": len(train_paths), "annotations": dict(train_counts)},
        "bench": {"images": len(bench_paths), "annotations": dict(bench_counts)},
        "demo": {"images": len(demo_paths), "annotations": dict(demo_counts)},
        "missing_datasets": sorted(set(missing)),
    }
    (SPLITS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written to {SPLITS_DIR}/manifest.json")

    if missing:
        unique_missing = sorted(set(missing))
        print(f"\nPendiente: descargar y convertir: {unique_missing}")
        print("Una vez descargados:")
        print(f"  python3 datasets/scripts/convert/convert_datasets.py "
              f"--datasets {' '.join(unique_missing)} --views canonical_v2")
        print("Luego volver a ejecutar este script.")


if __name__ == "__main__":
    main()
