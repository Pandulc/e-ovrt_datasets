"""Validador de clip_gt.v2 (spec 43 §5) — fixtures sintéticos."""
import copy
from pathlib import Path

from bench.validate_clip_gt import validate_gt, validate_manifest

VALID_GT = {
    "schema_version": "clip_gt.v2",
    "clip_id": "cb_a01_p1_cr01",
    "source_file": "clips/cb_a01_p1_cr01.mp4",
    "block": "A",
    "scenario": "P1",
    "fps_nominal": 30,
    "duration_ms": 32000,
    "recording": {"resolution": "1280x720", "distance_band_m": "5-10",
                  "lighting": "natural", "occlusion": "low"},
    "negative": False,
    "episodes": [
        {"id": "ep1", "condition_id": "CR-01", "level": "scene", "source_id": "cb_a01_p1_cr01",
         "start_ms": 4200, "end_ms": 21500, "subjects_in_evidence": 1, "notes": ""},
    ],
    "sub_threshold_events": [],
    "annotation": {"annotator": "a1", "double_annotated": False,
                   "second_annotator": None, "kappa": None,
                   "start_end_tolerance_ms": 500},
}


def test_gt_valido_sin_errores():
    assert validate_gt(copy.deepcopy(VALID_GT)) == []


def test_detecta_episodio_fuera_de_duracion():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["end_ms"] = 99000
    assert any("duration_ms" in e for e in validate_gt(gt))


def test_detecta_solape_de_misma_condicion():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"].append({"id": "ep2", "condition_id": "CR-01", "level": "scene",
                           "start_ms": 20000, "end_ms": 25000,
                           "subjects_in_evidence": 1, "notes": ""})
    assert any("solape" in e for e in validate_gt(gt))


def test_solape_permitido_entre_sujetos_distintos():
    gt = copy.deepcopy(VALID_GT)
    for ep, label in zip(gt["episodes"], ["persona_A"]):
        ep["level"] = "subject"; ep["subject_label"] = label; ep["subject_key"] = label
    gt["episodes"].append({"id": "ep2", "condition_id": "CR-01", "level": "subject",
                           "subject_label": "persona_B", "subject_key": "persona_B",
                           "start_ms": 5000,
                           "end_ms": 20000, "subjects_in_evidence": 1, "notes": ""})
    assert validate_gt(gt) == []


def test_detecta_negative_inconsistente():
    gt = copy.deepcopy(VALID_GT)
    gt["negative"] = True
    assert any("negative" in e for e in validate_gt(gt))


def test_i6_detecta_level_invalido():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["level"] = "clip"
    assert any("level" in e for e in validate_gt(gt))


def test_i6_detecta_subjects_in_evidence_invalido():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["subjects_in_evidence"] = 0
    assert any("subjects_in_evidence" in e for e in validate_gt(gt))


def test_i6_subjects_in_evidence_no_entero_invalido():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["subjects_in_evidence"] = 1.5
    assert any("subjects_in_evidence" in e for e in validate_gt(gt))


def test_i6_detecta_scene_con_subject_label():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["subject_label"] = "persona_A"  # level ya es "scene"
    assert any("subject_label" in e for e in validate_gt(gt))


def test_i6_detecta_sub_threshold_event_condition_invalida():
    gt = copy.deepcopy(VALID_GT)
    gt["sub_threshold_events"] = [
        {"condition_id": "CR-99", "start_ms": 100, "end_ms": 500, "reason": "x"},
    ]
    assert any("condition_id" in e for e in validate_gt(gt))


def test_i6_detecta_sub_threshold_event_start_end_invalidos():
    gt = copy.deepcopy(VALID_GT)
    gt["sub_threshold_events"] = [
        {"condition_id": "CR-01", "start_ms": 500, "end_ms": 100, "reason": "x"},
    ]
    assert any("inválidos" in e for e in validate_gt(gt))


def test_i6_detecta_sub_threshold_event_excede_duracion():
    gt = copy.deepcopy(VALID_GT)
    gt["sub_threshold_events"] = [
        {"condition_id": "CR-01", "start_ms": 100, "end_ms": 99000, "reason": "x"},
    ]
    assert any("duration_ms" in e for e in validate_gt(gt))


def test_i6_aviso_negativo_con_scenario_sospechoso(capsys):
    gt = copy.deepcopy(VALID_GT)
    gt["negative"] = True
    gt["episodes"] = []
    gt["scenario"] = "P1"
    errors = validate_gt(gt)
    assert errors == []
    out = capsys.readouterr().out
    assert "aviso" in out.lower()
    assert gt["clip_id"] in out


def test_i6_sin_aviso_para_negativo_p5():
    gt = copy.deepcopy(VALID_GT)
    gt["negative"] = True
    gt["episodes"] = []
    gt["scenario"] = "P5"
    validate_gt(gt)


def test_i6_sin_aviso_para_negativo_v3(capsys):
    gt = copy.deepcopy(VALID_GT)
    gt["negative"] = True
    gt["episodes"] = []
    gt["scenario"] = "V3"
    validate_gt(gt)
    assert capsys.readouterr().out == ""


def test_i6_sin_aviso_para_clip_positivo(capsys):
    gt = copy.deepcopy(VALID_GT)  # negative False, scenario P1
    validate_gt(gt)
    assert capsys.readouterr().out == ""


# FIX 2 (auditoría 2026-07-11): espejo exacto del contrato del evaluador
# (control-plane evaluation/temporal.py ClipEpisodeV2): scene exige
# source_id, subject exige subject_key.
def test_fix2_detecta_scene_sin_source_id():
    gt = copy.deepcopy(VALID_GT)
    del gt["episodes"][0]["source_id"]
    assert any("source_id" in e for e in validate_gt(gt))


def test_fix2_detecta_subject_sin_subject_key():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["level"] = "subject"
    gt["episodes"][0]["subject_label"] = "persona_A"
    assert any("subject_key" in e for e in validate_gt(gt))


def test_fix2_subject_con_subject_key_no_da_error_de_identidad():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["level"] = "subject"
    gt["episodes"][0]["subject_label"] = "persona_A"
    gt["episodes"][0]["subject_key"] = "persona_A"
    errors = validate_gt(gt)
    assert not any("subject_key" in e for e in errors)


def test_manifest_cruza_gt_y_checksum(tmp_path):
    gt_dir = tmp_path / "gt"; gt_dir.mkdir()
    clips = tmp_path / "clips"; clips.mkdir()
    (clips / "c1.mp4").write_bytes(b"fake video bytes")
    import hashlib, json
    sha = hashlib.sha256(b"fake video bytes").hexdigest()
    gt = copy.deepcopy(VALID_GT)
    gt["clip_id"] = "c1"; gt["source_file"] = "clips/c1.mp4"
    (gt_dir / "c1.json").write_text(json.dumps(gt))
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": sha,
                           "fps": 30, "duration_ms": 32000, "resolution": "1280x720",
                           "scenario": "P1", "block": "A", "gt": "gt/c1.json"}]}
    assert validate_manifest(manifest, tmp_path) == []
    manifest["clips"][0]["sha256"] = "f" * 64
    assert any("sha256" in e for e in validate_manifest(manifest, tmp_path))


# FIX 6 (auditoría 2026-07-11): validate_manifest debe cruzar source_file del
# GT contra el archivo listado en el manifest (GT promovido sin re-derivar /
# apuntando al clip equivocado).
def test_fix6_detecta_source_file_no_coincide_con_manifest(tmp_path):
    gt_dir = tmp_path / "gt"; gt_dir.mkdir()
    clips = tmp_path / "clips"; clips.mkdir()
    (clips / "c1.mp4").write_bytes(b"fake video bytes")
    import hashlib, json
    sha = hashlib.sha256(b"fake video bytes").hexdigest()
    gt = copy.deepcopy(VALID_GT)
    gt["clip_id"] = "c1"
    gt["source_file"] = "clips/otro_clip.mp4"  # no coincide con el manifest
    (gt_dir / "c1.json").write_text(json.dumps(gt))
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": sha,
                           "fps": 30, "duration_ms": 32000, "resolution": "1280x720",
                           "scenario": "P1", "block": "A", "gt": "gt/c1.json"}]}
    errors = validate_manifest(manifest, tmp_path)
    assert any("source_file" in e for e in errors)


# FIX 7 (auditoría 2026-07-11): filas del manifest sin gt/file/clip_id deben
# dar error claro por fila, no KeyError.
def test_fix7_fila_manifest_sin_campo_gt_da_error_claro(tmp_path):
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": "0" * 64}]}
    errors = validate_manifest(manifest, tmp_path)  # sin KeyError
    assert any("c1" in e and "gt" in e for e in errors)


def test_fix7_fila_manifest_sin_campo_file_da_error_claro(tmp_path):
    manifest = {"clips": [{"clip_id": "c1", "gt": "gt/c1.json", "sha256": "0" * 64}]}
    errors = validate_manifest(manifest, tmp_path)  # sin KeyError
    assert any("c1" in e and "file" in e for e in errors)


def test_fix7_fila_manifest_sin_campo_clip_id_da_error_claro(tmp_path):
    manifest = {"clips": [{"file": "clips/c1.mp4", "gt": "gt/c1.json", "sha256": "0" * 64}]}
    errors = validate_manifest(manifest, tmp_path)  # sin KeyError
    assert any("clip_id" in e for e in errors)


def test_fix7_gt_con_json_corrupto_da_error_claro(tmp_path):
    # Un gt/<id>.json con JSON roto propagaba json.JSONDecodeError crudo;
    # debe reportarse como error de validación indicando el archivo.
    gt_dir = tmp_path / "gt"; gt_dir.mkdir()
    (gt_dir / "c1.json").write_text("{esto no es json")
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4",
                           "sha256": "0" * 64, "gt": "gt/c1.json"}]}
    errors = validate_manifest(manifest, tmp_path)  # sin JSONDecodeError
    assert any("c1" in e and "gt/c1.json" in e and "JSON" in e for e in errors)


# FIX 8 (promote_clip.py, gap de auditoría 2026-07-11): una fila recién
# promovida sin GT todavía (state preannotated/corrected) no debe fallar por
# no traer `gt` — es el caso normal de un clip que no pasó por CVAT aún.
def test_fix8_fila_state_preannotated_sin_gt_no_falla(tmp_path):
    clips = tmp_path / "clips"; clips.mkdir()
    (clips / "c1.mp4").write_bytes(b"fake video bytes")
    import hashlib
    sha = hashlib.sha256(b"fake video bytes").hexdigest()
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": sha,
                           "state": "preannotated"}]}
    assert validate_manifest(manifest, tmp_path) == []


def test_fix8_fila_state_corrected_sin_gt_no_falla(tmp_path):
    clips = tmp_path / "clips"; clips.mkdir()
    (clips / "c1.mp4").write_bytes(b"fake video bytes")
    import hashlib
    sha = hashlib.sha256(b"fake video bytes").hexdigest()
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": sha,
                           "state": "corrected"}]}
    assert validate_manifest(manifest, tmp_path) == []


def test_fix8_fila_state_gt_ready_sin_gt_falla():
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": "0" * 64,
                           "state": "gt_ready"}]}
    errors = validate_manifest(manifest, Path("."))
    assert any("c1" in e and "gt" in e for e in errors)


def test_fix8_fila_state_gt_ready_con_gt_se_valida_igual(tmp_path):
    gt_dir = tmp_path / "gt"; gt_dir.mkdir()
    clips = tmp_path / "clips"; clips.mkdir()
    (clips / "c1.mp4").write_bytes(b"fake video bytes")
    import hashlib, json
    sha = hashlib.sha256(b"fake video bytes").hexdigest()
    gt = copy.deepcopy(VALID_GT)
    gt["clip_id"] = "c1"; gt["source_file"] = "clips/c1.mp4"
    (gt_dir / "c1.json").write_text(json.dumps(gt))
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": sha,
                           "state": "gt_ready", "gt": "gt/c1.json"}]}
    assert validate_manifest(manifest, tmp_path) == []
