"""Promoción de un clip del laboratorio (datasets-videos/) al banco (spec 43 §5,
extendido por el gap de auditoría 2026-07-11: sin este script, 8-15 clips
copiados a mano = inconsistencia garantizada). Fixtures sintéticos, sin media
real — un .mp4 fake de bytes alcanza."""
import hashlib
import json

import pytest
import yaml

from bench.promote_clip import PromoteClipError, promote_clip

CLIP_YAML = {
    "clip_id": "cb_b01_p7",
    "block": "B",
    "scenario": "P7",
    "level": "subject",
    "recording": {"resolution": "1920x1080", "distance_band_m": "5-10",
                  "lighting": "natural", "occlusion": "low"},
    "annotation": {"annotator": "a1", "double_annotated": False},
}

VALID_GT = {
    "schema_version": "clip_gt.v2",
    "clip_id": "cb_b01_p7",
    "source_file": "clips/cb_b01_p7.mp4",
    "block": "B",
    "scenario": "P7",
    "fps_nominal": 30,
    "duration_ms": 24433,
    "recording": {"resolution": "1920x1080", "distance_band_m": "5-10",
                  "lighting": "natural", "occlusion": "low"},
    "negative": False,
    "episodes": [
        {"id": "ep1", "condition_id": "CR-01", "level": "subject",
         "source_id": "cb_b01_p7", "subject_label": "persona_A",
         "subject_key": "persona_A", "start_ms": 1000, "end_ms": 5000,
         "subjects_in_evidence": 1, "notes": ""},
    ],
    "sub_threshold_events": [],
    "annotation": {"annotator": "a1", "double_annotated": False,
                   "second_annotator": None, "kappa": None,
                   "start_end_tolerance_ms": 500},
}


def _write_lab_clip(lab_dir, clip_id, mp4_bytes=b"fake video bytes",
                     clip_yaml=None, with_preann=True, with_corrected=False,
                     with_gt=False, sha_override=None):
    """Arma un clip de laboratorio mínimo (spec 43 §5 + video-gt-lab)."""
    clips_dir = lab_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = clips_dir / f"{clip_id}.mp4"
    mp4_path.write_bytes(mp4_bytes)
    sha = sha_override or hashlib.sha256(mp4_bytes).hexdigest()
    info = {
        "clip_id": clip_id,
        "file": f"clips/{clip_id}.mp4",
        "fps": 30,
        "duration_ms": 24433,
        "n_frames": 733,
        "resolution": "1920x1080",
        "sha256": sha,
    }
    (clips_dir / f"{clip_id}.info.json").write_text(json.dumps(info))

    if clip_yaml is not None:
        (lab_dir / f"{clip_id}.clip.yaml").write_text(yaml.safe_dump(clip_yaml))

    if with_preann:
        preann_dir = lab_dir / "preann"
        preann_dir.mkdir(parents=True, exist_ok=True)
        (preann_dir / f"{clip_id}.xml").write_text("<annotations/>")

    if with_corrected:
        corrected_dir = lab_dir / "corrected"
        corrected_dir.mkdir(parents=True, exist_ok=True)
        (corrected_dir / f"{clip_id}.xml").write_text("<annotations/>")

    if with_gt:
        gt_dir = lab_dir / "gt"
        gt_dir.mkdir(parents=True, exist_ok=True)
        (gt_dir / f"{clip_id}.json").write_text(json.dumps(VALID_GT))


def _bank_paths(tmp_path):
    return tmp_path / "bank", tmp_path / "raw_bench" / "clips"


def test_promocion_solo_preann_da_state_preannotated(tmp_path):
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    row = promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)

    assert row["state"] == "preannotated"
    assert row["clip_id"] == "cb_b01_p7"
    assert "annotations" not in row
    assert "gt" not in row
    assert (raw_bench_dir / "cb_b01_p7.mp4").exists()
    assert (bank_dir / "meta" / "cb_b01_p7.clip.yaml").exists()
    assert (bank_dir / "meta" / "cb_b01_p7.info.json").exists()
    assert (bank_dir / "preann" / "cb_b01_p7.xml").exists()

    manifest = yaml.safe_load((bank_dir / "manifest.yaml").read_text())
    assert len(manifest["clips"]) == 1
    assert manifest["clips"][0]["clip_id"] == "cb_b01_p7"
    assert manifest["clips"][0]["state"] == "preannotated"


def test_repromocion_es_idempotente_actualiza_no_duplica(tmp_path):
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)
    promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)

    # Ahora aparece el XML corregido en el laboratorio.
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML, with_corrected=True)
    row = promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)

    assert row["state"] == "corrected"
    manifest = yaml.safe_load((bank_dir / "manifest.yaml").read_text())
    assert len(manifest["clips"]) == 1  # no duplica
    assert manifest["clips"][0]["state"] == "corrected"
    assert manifest["clips"][0]["annotations"] == "annotations/cb_b01_p7.xml"
    assert (bank_dir / "annotations" / "cb_b01_p7.xml").exists()


def test_sha256_no_coincide_da_error_claro_y_no_copia(tmp_path):
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML,
                     sha_override="f" * 64)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    with pytest.raises(PromoteClipError, match="sha256"):
        promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)

    assert not (raw_bench_dir / "cb_b01_p7.mp4").exists()
    assert not bank_dir.exists()


def test_promocion_con_gt_valido_da_state_gt_ready(tmp_path):
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML,
                     with_corrected=True, with_gt=True)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    row = promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)

    assert row["state"] == "gt_ready"
    assert row["gt"] == "gt/cb_b01_p7.json"
    assert (bank_dir / "gt" / "cb_b01_p7.json").exists()


def test_state_override_explicito(tmp_path):
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML,
                     with_corrected=True, with_gt=True)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    row = promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir,
                        state_override="corrected")

    assert row["state"] == "corrected"


def test_falta_clip_yaml_da_error_claro(tmp_path):
    """Caso real: cb_b01_p7 tiene mp4+info.json pero todavía no tiene
    clip.yaml (lo crea el usuario) — el script no debe inventarlo."""
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=None)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    with pytest.raises(PromoteClipError, match="clip.yaml"):
        promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)


def test_falta_preann_da_error_claro(tmp_path):
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML, with_preann=False)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    with pytest.raises(PromoteClipError, match="preann"):
        promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)


def test_falta_mp4_da_error_claro(tmp_path):
    lab_dir = tmp_path / "lab"
    lab_dir.mkdir()
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    with pytest.raises(PromoteClipError, match="mp4|\\.mp4"):
        promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)


def test_orden_por_clip_id_con_dos_clips(tmp_path):
    lab_dir = tmp_path / "lab"
    yaml_z = dict(CLIP_YAML, clip_id="cb_z99_p1")
    yaml_a = dict(CLIP_YAML, clip_id="cb_a01_p1")
    _write_lab_clip(lab_dir, "cb_z99_p1", clip_yaml=yaml_z)
    _write_lab_clip(lab_dir, "cb_a01_p1", clip_yaml=yaml_a)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    promote_clip("cb_z99_p1", lab_dir, bank_dir, raw_bench_dir)
    promote_clip("cb_a01_p1", lab_dir, bank_dir, raw_bench_dir)

    manifest = yaml.safe_load((bank_dir / "manifest.yaml").read_text())
    ids = [c["clip_id"] for c in manifest["clips"]]
    assert ids == ["cb_a01_p1", "cb_z99_p1"]


def test_file_relativo_al_bank_dir_apunta_al_raw(tmp_path):
    lab_dir = tmp_path / "lab"
    _write_lab_clip(lab_dir, "cb_b01_p7", clip_yaml=CLIP_YAML)
    bank_dir, raw_bench_dir = _bank_paths(tmp_path)

    row = promote_clip("cb_b01_p7", lab_dir, bank_dir, raw_bench_dir)

    resolved = (bank_dir / row["file"]).resolve()
    assert resolved == (raw_bench_dir / "cb_b01_p7.mp4").resolve()
