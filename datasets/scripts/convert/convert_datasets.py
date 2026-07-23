#!/usr/bin/env python3
"""Convert raw PPE datasets into COCO, YOLO and ODVG formats."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "datasets" / "raw"
PROCESSED = ROOT / "datasets" / "processed"


CANONICAL_CLASSES = ["person", "helmet", "vest", "no_helmet", "no_vest"]


@dataclass(frozen=True)
class DatasetConfig:
    dataset_id: str
    source_format: str
    canonical_map: dict[str, str]
    raw_dir: Path | None = None
    image_dir: Path | None = None
    classes: list[str] | None = None
    yolo_label_dir: Path | None = None
    voc_label_dir: Path | None = None
    splits: dict[str, Path | list[str]] | None = None
    custom_split_seed: int = 42
    canonical_v2_map: dict[str, str] | None = None
    negative_classes: dict[str, str] | None = None  # ej: {"NO-Hardhat": "no_helmet", "NO-Safety Vest": "no_vest"}
    # Fuentes cuyo nombre cae en la lista prohibida de bare_head (head/face) pero
    # que se VERIFICÓ semánticamente que son anotaciones explícitas de cabeza
    # descubierta (no derivación por resta). Exige verificación empírica documentada
    # en el test del dataset (ej. shel5k: datasets/tests/test_shel5k_mapping.py).
    bare_head_explicit_sources: frozenset[str] | set[str] | None = None


def configs() -> dict[str, DatasetConfig]:
    return {
        "chv": DatasetConfig(
            dataset_id="chv",
            raw_dir=RAW / "chv" / "CHV_dataset",
            image_dir=RAW / "chv" / "CHV_dataset" / "images",
            source_format="yolo",
            yolo_label_dir=RAW / "chv" / "CHV_dataset" / "annotations",
            classes=[
                "person",
                "vest",
                "blue helmet",
                "red helmet",
                "white helmet",
                "yellow helmet",
            ],
            canonical_map={
                "person": "person",
                "vest": "vest",
                "blue helmet": "helmet",
                "red helmet": "helmet",
                "white helmet": "helmet",
                "yellow helmet": "helmet",
            },
            canonical_v2_map={
                "person": "person",
                "vest": "vest",
                "blue helmet": "helmet",
                "red helmet": "helmet",
                "white helmet": "helmet",
                "yellow helmet": "helmet",
            },
            splits={
                "train": RAW / "chv" / "CHV_dataset" / "data split" / "train.txt",
                "val": RAW / "chv" / "CHV_dataset" / "data split" / "valid.txt",
                "test": RAW / "chv" / "CHV_dataset" / "data split" / "test.txt",
            },
        ),
        "construction_site_safety": DatasetConfig(
            dataset_id="construction_site_safety",
            raw_dir=RAW / "construction_site_safety",
            image_dir=RAW / "construction_site_safety",
            source_format="yolo",
            yolo_label_dir=RAW / "construction_site_safety",
            classes=[
                "Hardhat",
                "Mask",
                "NO-Hardhat",
                "NO-Mask",
                "NO-Safety Vest",
                "Person",
                "Safety Cone",
                "Safety Vest",
                "machinery",
                "vehicle",
            ],
            canonical_map={},
            canonical_v2_map={
                "Person": "person",
                "Hardhat": "helmet",
                "Safety Vest": "vest",
                "NO-Hardhat": "bare_head",
            },
            negative_classes={
                "NO-Hardhat": "no_helmet",
                "NO-Safety Vest": "no_vest",
            },
            splits={
                "train": ["train"],
                "val": ["valid"],
                "test": ["test"],
            },
        ),
        "ppe_siabar": DatasetConfig(
            dataset_id="ppe_siabar",
            raw_dir=RAW / "ppe_siabar",
            image_dir=RAW / "ppe_siabar",
            source_format="yolo",
            yolo_label_dir=RAW / "ppe_siabar",
            classes=[
                "Boots",   # [0] from data.yaml
                "Helmet",  # [1]
                "Person",  # [2]
                "Vest",    # [3]
            ],
            canonical_map={},
            canonical_v2_map={
                "Person": "person",
                "Helmet": "helmet",
                "Vest": "vest",
            },
            splits={
                "train": ["train"],
                "val": ["valid"],
                "test": ["test"],
            },
        ),
        "construction_safety_hardhat": DatasetConfig(
            dataset_id="construction_safety_hardhat",
            raw_dir=RAW / "construction_safety_hardhat",
            image_dir=RAW / "construction_safety_hardhat",
            source_format="yolo",
            yolo_label_dir=RAW / "construction_safety_hardhat",
            classes=[
                "helmet",
                "no-helmet",
                "vest",
                "harness",
                "person",
            ],
            canonical_map={},
            canonical_v2_map={
                "person": "person",
                "helmet": "helmet",
                "vest": "vest",
                "no-helmet": "bare_head",
            },
            negative_classes={
                "no-helmet": "no_helmet",
            },
            splits=None,
        ),
        "construction_ppe": DatasetConfig(
            dataset_id="construction_ppe",
            raw_dir=RAW / "construction_ppe",
            image_dir=RAW / "construction_ppe" / "images",
            source_format="yolo",
            yolo_label_dir=RAW / "construction_ppe" / "labels",
            classes=[
                "helmet",
                "gloves",
                "vest",
                "boots",
                "goggles",
                "none",
                "Person",
                "no_helmet",
                "no_goggle",
                "no_gloves",
                "no_boots",
            ],
            canonical_map={
                "helmet": "helmet",
                "vest": "vest",
                "Person": "person",
                "no_helmet": "no_helmet",
            },
            canonical_v2_map={
                "Person": "person",
                "helmet": "helmet",
                "vest": "vest",
                "no_helmet": "bare_head",
            },
            splits={
                "train": ["train"],
                "val": ["val"],
                "test": ["test"],
            },
        ),
        "shel5k": DatasetConfig(
            dataset_id="shel5k",
            raw_dir=RAW / "shel5k" / "9rcv8mm682-4" / "Safety Helmet Wearing Dataset",
            image_dir=RAW
            / "shel5k"
            / "9rcv8mm682-4"
            / "Safety Helmet Wearing Dataset"
            / "Images",
            source_format="voc",
            voc_label_dir=RAW
            / "shel5k"
            / "9rcv8mm682-4"
            / "Safety Helmet Wearing Dataset"
            / "Annotations",
            classes=[
                "helmet",
                "head_with_helmet",
                "person_with_helmet",
                "head",
                "person_no_helmet",
                "face",
                "person",
            ],
            canonical_map={
                "helmet": "helmet",
                "head_with_helmet": "helmet",
                "person_with_helmet": "person",
                "person_no_helmet": "no_helmet",
                "head": "no_helmet",
                "face": "no_helmet",
                "person": "person",
            },
            canonical_v2_map={
                "person_with_helmet": "person",
                "person_no_helmet": "person",
                "person": "person",
                "helmet": "helmet",
                # head_with_helmet NO se mapea: solapa 97% con una caja `helmet`
                # separada (verificado sobre 400 XML) — mapearlo duplicaría el GT.
                # `head` en SHEL5K es la anotación EXPLÍCITA de cabeza descubierta
                # (82% contenida en person_no_helmet, 2% en person_with_helmet;
                # existe head_with_helmet aparte): cumple el contrato D9 vía
                # bare_head_explicit_sources. `face` sigue sin mapear.
                "head": "bare_head",
            },
            bare_head_explicit_sources=frozenset({"head"}),
            splits=None,
        ),
        "sh17": DatasetConfig(
            dataset_id="sh17",
            raw_dir=RAW / "sh17" / "kaggle",
            image_dir=RAW / "sh17" / "kaggle" / "images",
            source_format="yolo",
            yolo_label_dir=RAW / "sh17" / "kaggle" / "labels",
            voc_label_dir=RAW / "sh17" / "kaggle" / "voc_labels",
            classes=[
                "person",
                "ear",
                "ear-mufs",
                "face",
                "face-guard",
                "face-mask",
                "foot",
                "tool",
                "glasses",
                "gloves",
                "helmet",
                "hands",
                "head",
                "medical-suit",
                "shoes",
                "safety-suit",
                "safety-vest",
            ],
            canonical_map={
                "person": "person",
                "helmet": "helmet",
                "safety-vest": "vest",
                "head": "no_helmet",
                "face": "no_helmet",
            },
            canonical_v2_map={
                "person": "person",
                "helmet": "helmet",
                "safety-vest": "vest",
                # head and face are NOT mapped: bare_head from head/face is forbidden (D9)
            },
            splits={
                "train": RAW / "sh17" / "kaggle" / "train_files.txt",
                "val": RAW / "sh17" / "kaggle" / "val_files.txt",
            },
        ),
    }


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def image_files(image_dir: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return sorted(p for p in image_dir.rglob("*") if p.is_file() and p.suffix.lower() in exts)


def stem_to_image(paths: list[Path]) -> dict[str, Path]:
    return {p.stem: p for p in paths}


def split_from_text_file(path: Path, images_by_stem: dict[str, Path]) -> list[Path]:
    items: list[Path] = []
    for raw_line in path.read_text().splitlines():
        value = raw_line.strip()
        if not value:
            continue
        value_path = Path(value)
        stem = value_path.stem
        if stem in images_by_stem:
            items.append(images_by_stem[stem])
    return items


def split_from_subdirs(config: DatasetConfig) -> dict[str, list[Path]]:
    assert config.splits
    splits: dict[str, list[Path]] = {}
    for split_name, subdirs in config.splits.items():
        assert isinstance(subdirs, list)
        paths: list[Path] = []
        for subdir in subdirs:
            paths.extend(image_files(config.image_dir / subdir))
        splits[split_name] = sorted(paths)
    return splits


def custom_splits(paths: list[Path], seed: int) -> dict[str, list[Path]]:
    rng = random.Random(seed)
    shuffled = list(paths)
    rng.shuffle(shuffled)
    n = len(shuffled)
    train_n = int(n * 0.70)
    val_n = int(n * 0.15)
    return {
        "train": sorted(shuffled[:train_n]),
        "val": sorted(shuffled[train_n : train_n + val_n]),
        "test": sorted(shuffled[train_n + val_n :]),
    }


_SUBDIR_SPLIT_DATASETS = {"construction_ppe", "construction_site_safety", "ppe_siabar"}


def load_splits(config: DatasetConfig, paths: list[Path]) -> dict[str, list[Path]]:
    if config.dataset_id in _SUBDIR_SPLIT_DATASETS:
        return split_from_subdirs(config)
    if config.splits:
        images_by_stem = stem_to_image(paths)
        result: dict[str, list[Path]] = {}
        for split_name, split_ref in config.splits.items():
            if isinstance(split_ref, Path):
                result[split_name] = split_from_text_file(split_ref, images_by_stem)
        return result
    return custom_splits(paths, config.custom_split_seed)


def yolo_label_path(config: DatasetConfig, image_path: Path) -> Path:
    assert config.yolo_label_dir
    if config.dataset_id == "construction_ppe":
        # dataset/images/<split>/<stem>.jpg → dataset/labels/<split>/<stem>.txt
        split = image_path.parent.name
        return config.yolo_label_dir / split / f"{image_path.stem}.txt"
    if config.dataset_id in ("construction_site_safety", "ppe_siabar"):
        # Roboflow yolov8: dataset/<split>/images/<stem>.jpg → dataset/<split>/labels/<stem>.txt
        return image_path.parent.parent / "labels" / f"{image_path.stem}.txt"
    if config.dataset_id == "construction_safety_hardhat":
        # Kaggle: labels co-located with images (flat or per-class subdirs)
        return image_path.parent / f"{image_path.stem}.txt"
    return config.yolo_label_dir / f"{image_path.stem}.txt"


def parse_yolo(config: DatasetConfig, image_path: Path) -> list[dict]:
    label_path = yolo_label_path(config, image_path)
    width, height = image_size(image_path)
    objects: list[dict] = []
    if not label_path.exists():
        return objects
    for line_no, raw_line in enumerate(label_path.read_text().splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid YOLO line {label_path}:{line_no}: {raw_line}")
        class_id = int(parts[0])
        x_c, y_c, box_w, box_h = [float(x) for x in parts[1:]]
        x1 = (x_c - box_w / 2.0) * width
        y1 = (y_c - box_h / 2.0) * height
        x2 = (x_c + box_w / 2.0) * width
        y2 = (y_c + box_h / 2.0) * height
        x1, y1, x2, y2 = clip_xyxy(x1, y1, x2, y2, width, height)
        if x2 <= x1 or y2 <= y1:
            continue
        objects.append(
            {
                "category": config.classes[class_id],
                "bbox_xyxy": [x1, y1, x2, y2],
                "source_label": str(label_path),
            }
        )
    return objects


def parse_voc(config: DatasetConfig, image_path: Path) -> list[dict]:
    assert config.voc_label_dir
    label_path = config.voc_label_dir / f"{image_path.stem}.xml"
    if not label_path.exists():
        return []
    width, height = image_size(image_path)
    root = ET.parse(label_path).getroot()
    objects: list[dict] = []
    for obj in root.findall(".//object"):
        name = (obj.findtext("name") or "").strip()
        box = obj.find("bndbox")
        if not name or box is None:
            continue
        x1 = float(box.findtext("xmin"))
        y1 = float(box.findtext("ymin"))
        x2 = float(box.findtext("xmax"))
        y2 = float(box.findtext("ymax"))
        x1, y1, x2, y2 = clip_xyxy(x1, y1, x2, y2, width, height)
        if x2 <= x1 or y2 <= y1:
            continue
        objects.append(
            {
                "category": name,
                "bbox_xyxy": [x1, y1, x2, y2],
                "source_label": str(label_path),
            }
        )
    return objects


def clip_xyxy(
    x1: float, y1: float, x2: float, y2: float, width: int, height: int
) -> tuple[float, float, float, float]:
    return (
        max(0.0, min(float(width), x1)),
        max(0.0, min(float(height), y1)),
        max(0.0, min(float(width), x2)),
        max(0.0, min(float(height), y2)),
    )


def xyxy_to_xywh(box: list[float]) -> list[float]:
    x1, y1, x2, y2 = box
    return [x1, y1, x2 - x1, y2 - y1]


def xyxy_to_yolo(box: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = box
    box_w = x2 - x1
    box_h = y2 - y1
    return [
        (x1 + box_w / 2.0) / width,
        (y1 + box_h / 2.0) / height,
        box_w / width,
        box_h / height,
    ]


_FORBIDDEN_BARE_HEAD_SOURCES = {"head", "face", "head_with_helmet"}


def assert_no_derived_bare_head(config: DatasetConfig) -> None:
    """bare_head solo desde negativos explícitos; nunca desde head/face (spec §3.1)."""
    v2 = config.canonical_v2_map or {}
    explicit = {s.lower() for s in (config.bare_head_explicit_sources or ())}
    for src, dst in v2.items():
        if dst == "bare_head" and src.lower() in _FORBIDDEN_BARE_HEAD_SOURCES:
            if src.lower() in explicit:
                # Exención verificada: la clase es un negativo explícito del
                # dataset de origen (ver bare_head_explicit_sources).
                continue
            raise ValueError(
                f"{config.dataset_id}: bare_head derivado de '{src}' está prohibido (D9)."
            )


def category_maps(config: DatasetConfig, view: str) -> tuple[list[str], dict[str, int]]:
    if view == "original":
        names = config.classes
    elif view == "canonical_cr01_cr02":
        names = CANONICAL_CLASSES
    elif view == "canonical_v2":
        names = ["person", "helmet", "vest", "bare_head"]
        return names, {n: i for i, n in enumerate(names)}
    else:
        raise ValueError(f"Unknown view: {view}")
    return names, {name: idx for idx, name in enumerate(names)}


def transform_category(config: DatasetConfig, category: str, view: str) -> str | None:
    if view == "original":
        if config.dataset_id == "shel5k":
            return category if category in config.classes else None
        return category if category in config.classes else None
    if view == "canonical_v2":
        return (config.canonical_v2_map or {}).get(category)
    mapped = config.canonical_map.get(category)
    return mapped


def parse_objects(config: DatasetConfig, image_path: Path) -> list[dict]:
    if config.source_format == "yolo":
        return parse_yolo(config, image_path)
    if config.source_format == "voc":
        return parse_voc(config, image_path)
    raise ValueError(config.source_format)


def safe_relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_coco(
    config: DatasetConfig,
    view: str,
    split: str,
    paths: list[Path],
    out_dir: Path,
) -> dict:
    names, name_to_id = category_maps(config, view)
    images = []
    annotations = []
    ann_id = 1
    dropped = Counter()
    class_counts = Counter()
    for image_id, image_path in enumerate(paths, 1):
        width, height = image_size(image_path)
        images.append(
            {
                "id": image_id,
                "file_name": safe_relpath(image_path),
                "width": width,
                "height": height,
            }
        )
        for obj in parse_objects(config, image_path):
            category = transform_category(config, obj["category"], view)
            if category is None:
                dropped[obj["category"]] += 1
                continue
            x, y, w, h = xyxy_to_xywh(obj["bbox_xyxy"])
            if w <= 0 or h <= 0:
                continue
            category_id = name_to_id[category]
            annotations.append(
                {
                    "id": ann_id,
                    "image_id": image_id,
                    "category_id": category_id,
                    "bbox": [round(x, 6), round(y, 6), round(w, 6), round(h, 6)],
                    "area": round(w * h, 6),
                    "iscrowd": 0,
                    "segmentation": [],
                }
            )
            ann_id += 1
            class_counts[category] += 1
    coco = {
        "info": {
            "description": f"{config.dataset_id} {view} {split}",
            "version": "dataset-v0.1",
        },
        "licenses": [],
        "images": images,
        "annotations": annotations,
        "categories": [{"id": idx, "name": name} for idx, name in enumerate(names)],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{split}.json"
    out_file.write_text(json.dumps(coco, indent=2))
    return {
        "file": safe_relpath(out_file),
        "images": len(images),
        "annotations": len(annotations),
        "class_counts": dict(class_counts),
        "dropped_source_classes": dict(dropped),
    }


def write_odvg(
    config: DatasetConfig,
    view: str,
    split: str,
    paths: list[Path],
    out_dir: Path,
) -> dict:
    names, name_to_id = category_maps(config, view)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{split}.jsonl"
    label_map_file = out_dir / "label_map.json"
    label_map_file.write_text(json.dumps({str(i): name for i, name in enumerate(names)}, indent=2))
    class_counts = Counter()
    dropped = Counter()
    lines = 0
    with out_file.open("w") as f:
        for image_path in paths:
            width, height = image_size(image_path)
            instances = []
            for obj in parse_objects(config, image_path):
                category = transform_category(config, obj["category"], view)
                if category is None:
                    dropped[obj["category"]] += 1
                    continue
                instances.append(
                    {
                        "bbox": [round(v, 6) for v in obj["bbox_xyxy"]],
                        "label": name_to_id[category],
                        "category": category,
                    }
                )
                class_counts[category] += 1
            item = {
                "filename": safe_relpath(image_path),
                "height": height,
                "width": width,
                "detection": {"instances": instances},
            }
            f.write(json.dumps(item) + "\n")
            lines += 1
    return {
        "file": safe_relpath(out_file),
        "label_map": safe_relpath(label_map_file),
        "images": lines,
        "annotations": sum(class_counts.values()),
        "class_counts": dict(class_counts),
        "dropped_source_classes": dict(dropped),
    }


def write_yolo(
    config: DatasetConfig,
    view: str,
    split: str,
    paths: list[Path],
    out_dir: Path,
) -> dict:
    names, name_to_id = category_maps(config, view)
    labels_dir = out_dir / "labels" / split
    image_list_dir = out_dir / "image_lists"
    labels_dir.mkdir(parents=True, exist_ok=True)
    image_list_dir.mkdir(parents=True, exist_ok=True)
    class_counts = Counter()
    dropped = Counter()
    list_file = image_list_dir / f"{split}.txt"
    with list_file.open("w") as image_list:
        for image_path in paths:
            width, height = image_size(image_path)
            image_list.write(str(image_path.resolve()) + "\n")
            lines = []
            for obj in parse_objects(config, image_path):
                category = transform_category(config, obj["category"], view)
                if category is None:
                    dropped[obj["category"]] += 1
                    continue
                yolo = xyxy_to_yolo(obj["bbox_xyxy"], width, height)
                if any(v < 0 or v > 1 for v in yolo) or yolo[2] <= 0 or yolo[3] <= 0:
                    continue
                lines.append(
                    "{} {}".format(
                        name_to_id[category],
                        " ".join(f"{v:.8f}" for v in yolo),
                    )
                )
                class_counts[category] += 1
            (labels_dir / f"{image_path.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
    data_yaml = out_dir / "data.yaml"
    split_lines = [f"{name}: {safe_relpath(image_list_dir / f'{name}.txt')}" for name in ["train", "val", "test"] if (image_list_dir / f"{name}.txt").exists()]
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {safe_relpath(out_dir)}",
                *split_lines,
                f"nc: {len(names)}",
                "names:",
                *[f"  {idx}: {name}" for idx, name in enumerate(names)],
                "",
            ]
        )
    )
    return {
        "labels_dir": safe_relpath(labels_dir),
        "image_list": safe_relpath(list_file),
        "data_yaml": safe_relpath(data_yaml),
        "images": len(paths),
        "annotations": sum(class_counts.values()),
        "class_counts": dict(class_counts),
        "dropped_source_classes": dict(dropped),
    }


def convert_dataset(dataset_id: str, views: list[str]) -> dict:
    config = configs()[dataset_id]
    if "canonical_v2" in views:
        assert_no_derived_bare_head(config)
    paths = image_files(config.image_dir)
    splits = load_splits(config, paths)
    report = {
        "dataset_id": dataset_id,
        "source_format": config.source_format,
        "raw_image_count": len(paths),
        "splits": {name: len(items) for name, items in splits.items()},
        "views": {},
    }
    for view in views:
        view_report = {"coco": {}, "yolo": {}, "odvg": {}}
        for split, split_paths in splits.items():
            view_report["coco"][split] = write_coco(
                config,
                view,
                split,
                split_paths,
                PROCESSED / "coco" / view / dataset_id,
            )
            view_report["yolo"][split] = write_yolo(
                config,
                view,
                split,
                split_paths,
                PROCESSED / "yolo" / view / dataset_id,
            )
            view_report["odvg"][split] = write_odvg(
                config,
                view,
                split,
                split_paths,
                PROCESSED / "odvg" / view / dataset_id,
            )
        report["views"][view] = view_report
    report_dir = PROCESSED / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"{dataset_id}_conversion_report.json"
    report_file.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["construction_site_safety", "chv", "ppe_siabar"],
        choices=sorted(configs()),
    )
    parser.add_argument(
        "--views",
        nargs="+",
        default=["canonical_v2"],
        choices=["original", "canonical_v2"],
    )
    args = parser.parse_args()

    summary = {}
    for dataset_id in args.datasets:
        summary[dataset_id] = convert_dataset(dataset_id, args.views)
        print(json.dumps({"converted": dataset_id, "splits": summary[dataset_id]["splits"]}))
    (PROCESSED / "reports" / "conversion_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
