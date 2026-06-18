import yaml
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / "registry" / "annotation_contract_v2.yaml"

def test_contract_defines_all_v2_classes():
    data = yaml.safe_load(CONTRACT.read_text())
    assert set(data["classes"]) == {"person", "helmet", "vest", "bare_head"}

def test_every_selected_dataset_declares_exhaustiveness():
    data = yaml.safe_load(CONTRACT.read_text())
    for ds, m in data["sources"].items():
        for cls in data["classes"]:
            assert m.get(cls) in {"exhaustiva", "parcial", "ausente"}, (ds, cls)
