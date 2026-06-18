#!/usr/bin/env python3
"""DEPRECATED (as of 2026-06-17) — replaced by canonical_v2 role splits.

Do NOT run. The v2 workflow uses build_role_views.py; fine-tuning subsets are
superseded by the TRAIN/BENCH/DEMO role manifests in datasets/splits/v2/.
"""
import sys
sys.exit("ERROR: generate_finetuning_cr01_cr02.py is DEPRECATED. Use build_role_views.py instead.")

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
CANONICAL_COCO = ROOT / "datasets" / "processed" / "coco" / "canonical_cr01_cr02"
PROCESSED = ROOT / "datasets" / "processed"
SPLITS = ROOT / "datasets" / "splits" / "cr01_cr02"

VIEW_NAME = "finetuning_cr01_cr02"
CANONICAL_CLASSES = ["person", "helmet", "vest", "no_helmet", "no_vest"]
ALLOWED_LABEL_SETS = {
    frozenset({"helmet"}),
    frozenset({"vest"}),
    frozenset({"helmet", "vest"}),
    frozenset({"helmet", "person"}),
    frozenset({"person", "vest"}),
    frozenset({"helmet", "person", "vest"}),
    frozenset({"person", "no_helmet"}),
    frozenset({"helmet", "person", "no_helmet"}),
    frozenset({"person", "no_helmet", "vest"}),
    frozenset({"helmet", "person", "no_helmet", "vest"}),
    frozenset({"no_helmet", "vest"}),
}


def safe_relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def xywh_to_yolo(bbox: list[float], width: int, height: int) -> list[float]:
    x, y, w, h = bbox
    return [
        (x + w / 2.0) / width,
        (y + h / 2.0) / height,
        w / width,
        h / height,
    ]


def xywh_to_xyxy(bbox: list[float]) -> list[float]:
    x, y, w, h = bbox
    return [x, y, x + w, y + h]


def load_view_manifest() -> dict[str, dict[str, str]]:
    path = SPLITS / "view_manifest.csv"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        return {row["source_image"]: row for row in csv.DictReader(fh)}


def load_coco(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def should_keep_image(labels: set[str]) -> bool:
    return frozenset(labels) in ALLOWED_LABEL_SETS


def filter_coco(data: dict) -> tuple[dict, dict[int, list[dict]]]:
    annotations_by_image: dict[int, list[dict]] = defaultdict(list)
    for annotation in data["annotations"]:
        annotations_by_image[annotation["image_id"]].append(annotation)

    images = []
    annotations = []
    old_to_new_image_id: dict[int, int] = {}
    next_ann_id = 1

    for image in data["images"]:
        image_annotations = annotations_by_image.get(image["id"], [])
        if not image_annotations:
            continue
        image_labels = {
            data["categories"][annotation["category_id"]]["name"]
            for annotation in image_annotations
        }
        if not should_keep_image(image_labels):
            continue
        new_image_id = len(images) + 1
        old_to_new_image_id[image["id"]] = new_image_id
        new_image = dict(image)
        new_image["id"] = new_image_id
        images.append(new_image)

        for annotation in image_annotations:
            new_annotation = dict(annotation)
            new_annotation["id"] = next_ann_id
            new_annotation["image_id"] = new_image_id
            annotations.append(new_annotation)
            next_ann_id += 1

    filtered = {
        "info": {
            **data.get("info", {}),
            "description": f"{data.get('info', {}).get('description', '')} curated fine-tuning",
            "view": VIEW_NAME,
            "curation_rule": "Keep only approved fine-tuning label-set combinations.",
        },
        "licenses": data.get("licenses", []),
        "images": images,
        "annotations": annotations,
        "categories": data["categories"],
    }
    filtered_annotations_by_image: dict[int, list[dict]] = defaultdict(list)
    for annotation in annotations:
        filtered_annotations_by_image[annotation["image_id"]].append(annotation)
    return filtered, filtered_annotations_by_image


def write_coco(dataset_id: str, split: str, data: dict) -> Path:
    out_dir = PROCESSED / "coco" / VIEW_NAME / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{split}.json"
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out_file


def write_yolo(dataset_id: str, split: str, data: dict, annotations_by_image: dict[int, list[dict]]) -> dict:
    out_dir = PROCESSED / "yolo" / VIEW_NAME / dataset_id
    labels_dir = out_dir / "labels" / split
    image_lists_dir = out_dir / "image_lists"
    labels_dir.mkdir(parents=True, exist_ok=True)
    image_lists_dir.mkdir(parents=True, exist_ok=True)

    list_file = image_lists_dir / f"{split}.txt"
    class_counts = Counter()
    with list_file.open("w", encoding="utf-8") as image_list:
        for image in data["images"]:
            image_path = ROOT / image["file_name"]
            image_list.write(str(image_path.resolve()) + "\n")
            lines = []
            for annotation in annotations_by_image[image["id"]]:
                class_id = annotation["category_id"]
                yolo = xywh_to_yolo(annotation["bbox"], image["width"], image["height"])
                if any(value < 0 or value > 1 for value in yolo):
                    continue
                lines.append(
                    "{} {}".format(
                        class_id,
                        " ".join(f"{value:.8f}" for value in yolo),
                    )
                )
                class_counts[CANONICAL_CLASSES[class_id]] += 1
            (labels_dir / f"{Path(image['file_name']).stem}.txt").write_text(
                "\n".join(lines) + "\n",
                encoding="utf-8",
            )

    data_yaml = out_dir / "data.yaml"
    split_lines = [
        f"{name}: {safe_relpath(image_lists_dir / f'{name}.txt')}"
        for name in ["train", "val", "test"]
        if (image_lists_dir / f"{name}.txt").exists()
    ]
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {safe_relpath(out_dir)}",
                *split_lines,
                f"nc: {len(CANONICAL_CLASSES)}",
                "names:",
                *[f"  {idx}: {name}" for idx, name in enumerate(CANONICAL_CLASSES)],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "labels_dir": safe_relpath(labels_dir),
        "image_list": safe_relpath(list_file),
        "data_yaml": safe_relpath(data_yaml),
        "class_counts": dict(class_counts),
    }


def write_odvg(dataset_id: str, split: str, data: dict, annotations_by_image: dict[int, list[dict]]) -> dict:
    out_dir = PROCESSED / "odvg" / VIEW_NAME / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{split}.jsonl"
    label_map = out_dir / "label_map.json"
    label_map.write_text(
        json.dumps({str(idx): name for idx, name in enumerate(CANONICAL_CLASSES)}, indent=2),
        encoding="utf-8",
    )

    class_counts = Counter()
    with out_file.open("w", encoding="utf-8") as fh:
        for image in data["images"]:
            instances = []
            for annotation in annotations_by_image[image["id"]]:
                class_id = annotation["category_id"]
                instances.append(
                    {
                        "bbox": [round(value, 6) for value in xywh_to_xyxy(annotation["bbox"])],
                        "label": class_id,
                        "category": CANONICAL_CLASSES[class_id],
                    }
                )
                class_counts[CANONICAL_CLASSES[class_id]] += 1
            fh.write(
                json.dumps(
                    {
                        "filename": image["file_name"],
                        "height": image["height"],
                        "width": image["width"],
                        "detection": {"instances": instances},
                    }
                )
                + "\n"
            )
    return {
        "file": safe_relpath(out_file),
        "label_map": safe_relpath(label_map),
        "class_counts": dict(class_counts),
    }


def write_manifest(rows: list[dict[str, str]]) -> Path:
    out_file = SPLITS / "finetuning_manifest.csv"
    fieldnames = [
        "dataset_id",
        "split",
        "source_image",
        "source_annotation",
        "canonical_conditions",
        "canonical_labels",
        "canonical_annotation_count",
        "hash_sha256",
        "notes",
    ]
    with out_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out_file


def process_dataset_split(
    coco_path: Path,
    view_rows: dict[str, dict[str, str]],
) -> tuple[dict, list[dict[str, str]]]:
    dataset_id = coco_path.parent.name
    split = coco_path.stem
    source = load_coco(coco_path)
    filtered, annotations_by_image = filter_coco(source)

    coco_out = write_coco(dataset_id, split, filtered)
    yolo_report = write_yolo(dataset_id, split, filtered, annotations_by_image)
    odvg_report = write_odvg(dataset_id, split, filtered, annotations_by_image)

    categories = {category["id"]: category["name"] for category in filtered["categories"]}
    class_counts = Counter(categories[annotation["category_id"]] for annotation in filtered["annotations"])

    manifest_rows = []
    for image in filtered["images"]:
        existing = view_rows.get(image["file_name"], {})
        manifest_rows.append(
            {
                "dataset_id": dataset_id,
                "split": split,
                "source_image": image["file_name"],
                "source_annotation": existing.get("source_annotation", ""),
                "canonical_conditions": existing.get("canonical_conditions", ""),
                "canonical_labels": existing.get("canonical_labels", ""),
                "canonical_annotation_count": existing.get(
                    "canonical_annotation_count",
                    str(len(annotations_by_image[image["id"]])),
                ),
                "hash_sha256": existing.get("hash_sha256", ""),
                "notes": existing.get("notes", ""),
            }
        )

    report = {
        "dataset_id": dataset_id,
        "split": split,
        "source_file": safe_relpath(coco_path),
        "coco_file": safe_relpath(coco_out),
        "images": len(filtered["images"]),
        "annotations": len(filtered["annotations"]),
        "class_counts": dict(class_counts),
        "yolo": yolo_report,
        "odvg": odvg_report,
    }
    return report, manifest_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-view",
        type=Path,
        default=CANONICAL_COCO,
        help="Directorio COCO canonical_cr01_cr02.",
    )
    args = parser.parse_args()

    view_rows = load_view_manifest()
    reports = []
    manifest_rows = []
    for coco_path in sorted(args.source_view.glob("*/*.json")):
        report, rows = process_dataset_split(coco_path, view_rows)
        reports.append(report)
        manifest_rows.extend(rows)

    manifest_path = write_manifest(manifest_rows)
    summary = {
        "view": VIEW_NAME,
        "curation_rule": "Keep only approved fine-tuning label-set combinations.",
        "manifest": safe_relpath(manifest_path),
        "total_images": sum(report["images"] for report in reports),
        "total_annotations": sum(report["annotations"] for report in reports),
        "class_counts": dict(
            sum((Counter(report["class_counts"]) for report in reports), Counter())
        ),
        "splits": {
            split: {
                "images": sum(report["images"] for report in reports if report["split"] == split),
                "annotations": sum(
                    report["annotations"] for report in reports if report["split"] == split
                ),
            }
            for split in ["train", "val", "test"]
        },
        "datasets": reports,
    }
    reports_dir = PROCESSED / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_path = reports_dir / f"{VIEW_NAME}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(yaml.safe_dump({k: summary[k] for k in ["view", "total_images", "total_annotations", "class_counts", "splits"]}, sort_keys=False))


if __name__ == "__main__":
    main()

