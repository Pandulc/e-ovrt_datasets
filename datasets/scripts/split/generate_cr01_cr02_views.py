#!/usr/bin/env python3
"""Generate derived CR-01/CR-02 manifests from canonical COCO annotations."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CANONICAL_COCO = ROOT / "datasets" / "processed" / "coco" / "canonical_cr01_cr02"
OUT_DIR = ROOT / "datasets" / "splits" / "cr01_cr02"

CONDITION_CLASSES = {"no_helmet", "no_vest"}
CANONICAL_CONTEXT_CLASSES = {"person", "helmet", "vest"}


def classify(labels: set[str]) -> str:
    if labels & CONDITION_CLASSES:
        return "condition_positive"
    if labels & CANONICAL_CONTEXT_CLASSES:
        return "canonical_positive_context"
    return "no_canonical_annotations"


def load_existing_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return {row["source_image"]: row for row in rows}


def iter_canonical_rows(existing: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for coco_path in sorted(CANONICAL_COCO.glob("*/*.json")):
        dataset_id = coco_path.parent.name
        split = coco_path.stem
        data = json.loads(coco_path.read_text(encoding="utf-8"))
        categories = {category["id"]: category["name"] for category in data["categories"]}

        labels_by_image_id: dict[int, list[str]] = defaultdict(list)
        for annotation in data["annotations"]:
            labels_by_image_id[annotation["image_id"]].append(categories[annotation["category_id"]])

        for image in data["images"]:
            source_image = image["file_name"]
            labels = labels_by_image_id.get(image["id"], [])
            label_set = set(labels)
            manifest_row = existing.get(source_image, {})
            row = {
                "dataset_id": dataset_id,
                "split": split,
                "view": classify(label_set),
                "source_image": source_image,
                "source_annotation": manifest_row.get("source_annotation", ""),
                "canonical_conditions": manifest_row.get("canonical_conditions", ""),
                "canonical_labels": "|".join(sorted(label_set)),
                "canonical_annotation_count": str(len(labels)),
                "hash_sha256": manifest_row.get("hash_sha256", ""),
                "notes": manifest_row.get("notes", ""),
            }
            rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset_id",
        "split",
        "view",
        "source_image",
        "source_annotation",
        "canonical_conditions",
        "canonical_labels",
        "canonical_annotation_count",
        "hash_sha256",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: list[dict[str, str]]) -> dict:
    by_view = Counter(row["view"] for row in rows)
    by_split_view: dict[str, Counter] = defaultdict(Counter)
    by_dataset_view: dict[str, Counter] = defaultdict(Counter)
    by_dataset_split_view: dict[str, Counter] = defaultdict(Counter)

    for row in rows:
        by_split_view[row["split"]][row["view"]] += 1
        by_dataset_view[row["dataset_id"]][row["view"]] += 1
        by_dataset_split_view[f"{row['dataset_id']}:{row['split']}"][row["view"]] += 1

    return {
        "total_images": len(rows),
        "view_counts": dict(by_view),
        "split_view_counts": {key: dict(value) for key, value in sorted(by_split_view.items())},
        "dataset_view_counts": {key: dict(value) for key, value in sorted(by_dataset_view.items())},
        "dataset_split_view_counts": {
            key: dict(value) for key, value in sorted(by_dataset_split_view.items())
        },
        "view_definitions": {
            "condition_positive": "Imagen con al menos una anotacion canonica no_helmet o no_vest.",
            "canonical_positive_context": (
                "Imagen sin no_helmet/no_vest, pero con person, helmet o vest."
            ),
            "no_canonical_annotations": (
                "Imagen que queda sin anotaciones luego del remapeo canonico CR-01/CR-02."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_DIR,
        help="Directorio destino para los manifests derivados.",
    )
    parser.add_argument(
        "--existing-manifest",
        type=Path,
        default=OUT_DIR / "split_manifest.csv",
        help="Manifest existente usado para copiar hash/notas/anotacion fuente.",
    )
    args = parser.parse_args()

    existing = load_existing_manifest(args.existing_manifest)
    rows = iter_canonical_rows(existing)
    write_csv(args.out_dir / "view_manifest.csv", rows)

    for view_name in [
        "condition_positive",
        "canonical_positive_context",
        "no_canonical_annotations",
    ]:
        write_csv(
            args.out_dir / f"{view_name}_manifest.csv",
            [row for row in rows if row["view"] == view_name],
        )

    summary = build_summary(rows)
    (args.out_dir / "view_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["view_counts"], sort_keys=True))


if __name__ == "__main__":
    main()

