import pytest
from convert.convert_datasets import DatasetConfig, assert_no_derived_bare_head

def test_guard_rejects_head_to_bare_head():
    cfg = DatasetConfig(
        dataset_id="x", source_format="yolo", canonical_map={},
        canonical_v2_map={"head": "bare_head"},
    )
    with pytest.raises(ValueError):
        assert_no_derived_bare_head(cfg)

def test_guard_allows_explicit_negative():
    cfg = DatasetConfig(
        dataset_id="x", source_format="yolo", canonical_map={},
        canonical_v2_map={"NO-Hardhat": "bare_head"},
    )
    assert assert_no_derived_bare_head(cfg) is None
