"""Tests for yolo_label_path — verifies each dataset's label path branch."""
from pathlib import Path

from convert.convert_datasets import DatasetConfig, yolo_label_path


def _cfg(dataset_id: str, yolo_label_dir: Path | None = None) -> DatasetConfig:
    return DatasetConfig(
        dataset_id=dataset_id,
        source_format="yolo",
        canonical_map={},
        yolo_label_dir=yolo_label_dir,
    )


def test_construction_ppe_uses_split_subdir():
    # construction_ppe: images/<split>/<stem>.jpg → labels/<split>/<stem>.txt
    label_dir = Path("/data/construction_ppe/labels")
    cfg = _cfg("construction_ppe", yolo_label_dir=label_dir)
    img = Path("/data/construction_ppe/images/train/worker01.jpg")
    assert yolo_label_path(cfg, img) == label_dir / "train" / "worker01.txt"


def test_construction_site_safety_roboflow_layout():
    # Roboflow yolov8: <split>/images/<stem>.jpg → <split>/labels/<stem>.txt
    cfg = _cfg("construction_site_safety", yolo_label_dir=Path("/data"))
    img = Path("/data/construction_site_safety/train/images/site001.jpg")
    expected = Path("/data/construction_site_safety/train/labels/site001.txt")
    assert yolo_label_path(cfg, img) == expected


def test_ppe_siabar_roboflow_layout():
    # Same Roboflow yolov8 layout as construction_site_safety
    cfg = _cfg("ppe_siabar", yolo_label_dir=Path("/data"))
    img = Path("/data/ppe_siabar/valid/images/worker99.jpg")
    expected = Path("/data/ppe_siabar/valid/labels/worker99.txt")
    assert yolo_label_path(cfg, img) == expected


def test_construction_safety_hardhat_colocated():
    # Kaggle dataset: label in same directory as image (flat or per-class subdir)
    cfg = _cfg("construction_safety_hardhat", yolo_label_dir=Path("/data"))
    img = Path("/data/construction_safety_hardhat/helmet/site42.jpg")
    expected = Path("/data/construction_safety_hardhat/helmet/site42.txt")
    assert yolo_label_path(cfg, img) == expected


def test_chv_flat_fallback():
    # chv has a dedicated label dir; no special branch → fallback to label_dir/<stem>.txt
    label_dir = Path("/data/chv/annotations")
    cfg = _cfg("chv", yolo_label_dir=label_dir)
    img = Path("/data/chv/images/person001.jpg")
    assert yolo_label_path(cfg, img) == label_dir / "person001.txt"
