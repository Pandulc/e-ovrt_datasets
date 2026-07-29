"""Tests del kit de auditoría visual para Task 4.3 (bench_gt_audit.md).

Lógica pura con fixtures sintéticas; los tests que requieren artefactos
reales (GT curado / imágenes raw) se marcan con skipif.
"""
import json
from pathlib import Path

import pytest
from PIL import Image

from bench.build_audit_kit import (
    COLOR_BARE_HEAD,
    COLOR_COMPLIANT,
    COLOR_VIOLATOR,
    coco_bbox_to_xyxy,
    group_records_by_image,
    output_name,
    person_label,
    readme_text,
    render_audit_image,
    sample_audit_images,
    stratify_images,
    summarize_image_gt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CURATED = REPO_ROOT / "datasets/processed/coco/bench/curated"
PERSON_GT = CURATED / "person_gt_bench_obra.json"

needs_artifacts = pytest.mark.skipif(
    not PERSON_GT.exists(), reason="requiere person_gt_bench_obra.json generado"
)


def _rec(fname, has_helmet, bbox=(0, 0, 50, 100)):
    return {
        "file_name": fname,
        "has_helmet": has_helmet,
        "has_vest": True,
        "person_bbox": list(bbox),
    }


# ---------------------------------------------------------------- estratificación

def test_group_records_by_image():
    recs = [_rec("a.jpg", True), _rec("a.jpg", False), _rec("b.jpg", True)]
    by_img = group_records_by_image(recs)
    assert set(by_img) == {"a.jpg", "b.jpg"}
    assert len(by_img["a.jpg"]) == 2


def test_stratify_separates_violator_and_compliant_images():
    recs = [
        _rec("viol.jpg", True),
        _rec("viol.jpg", False),   # una persona sin casco → imagen violadora
        _rec("conf.jpg", True),
        _rec("conf2.jpg", True),
    ]
    viol, conf = stratify_images(group_records_by_image(recs))
    assert viol == ["viol.jpg"]
    assert conf == ["conf.jpg", "conf2.jpg"]


def test_stratify_returns_sorted_lists():
    recs = [_rec("z.jpg", False), _rec("a.jpg", False), _rec("m.jpg", True)]
    viol, conf = stratify_images(group_records_by_image(recs))
    assert viol == ["a.jpg", "z.jpg"]
    assert conf == ["m.jpg"]


# ---------------------------------------------------------------- muestreo

def test_sample_is_deterministic_for_same_seed():
    viol = [f"v{i}.jpg" for i in range(30)]
    conf = [f"c{i}.jpg" for i in range(70)]
    s1 = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=43)
    s2 = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=43)
    assert s1 == s2
    assert len(s1) == 24


def test_sample_respects_strata_counts():
    viol = [f"v{i}.jpg" for i in range(30)]
    conf = [f"c{i}.jpg" for i in range(70)]
    sampled = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=43)
    n_viol = sum(1 for f in sampled if f.startswith("v"))
    n_conf = sum(1 for f in sampled if f.startswith("c"))
    assert n_viol == 12
    assert n_conf == 12
    assert len(set(sampled)) == 24  # sin duplicados


def test_sample_caps_at_available_images():
    viol = ["v0.jpg", "v1.jpg"]
    conf = ["c0.jpg"]
    sampled = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=43)
    assert sorted(sampled) == ["c0.jpg", "v0.jpg", "v1.jpg"]


def test_different_seed_changes_sample():
    viol = [f"v{i}.jpg" for i in range(30)]
    conf = [f"c{i}.jpg" for i in range(70)]
    s43 = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=43)
    s7 = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=7)
    assert s43 != s7


# ---------------------------------------------------------------- resúmenes / naming

def test_summarize_mixed_image():
    recs = [_rec("a.jpg", True), _rec("a.jpg", True), _rec("a.jpg", False)]
    assert summarize_image_gt(recs) == "3 personas: 2 con casco, 1 sin casco"


def test_summarize_single_compliant_person():
    assert summarize_image_gt([_rec("a.jpg", True)]) == "1 persona: 1 con casco"


def test_summarize_all_violators_omits_compliant_part():
    recs = [_rec("a.jpg", False), _rec("a.jpg", False)]
    assert summarize_image_gt(recs) == "2 personas: 2 sin casco"


def test_person_label():
    assert person_label(True) == "con casco"
    assert person_label(False) == "sin casco"


def test_output_name_numbers_and_keeps_stem():
    fname = "datasets/raw/construction_site_safety/valid/images/foo_jpg.rf.abc123.jpg"
    assert output_name(1, fname) == "01_foo_jpg.rf.abc123.png"
    assert output_name(24, fname) == "24_foo_jpg.rf.abc123.png"


def test_coco_bbox_to_xyxy():
    assert coco_bbox_to_xyxy([10.0, 20.0, 30.0, 40.0]) == [10.0, 20.0, 40.0, 60.0]


def test_readme_interpola_seed_y_conteos_reales():
    # El README del kit debe reflejar los parámetros REALES de generación:
    # regenerado con --seed/--n-violators distintos no puede decir "seed=43: 12+12".
    text = readme_text(seed=7, n_violators=5, n_compliant=3)
    assert "seed=7" in text
    assert "5 imágenes con ≥1 violador" in text
    assert "3 solo conformes" in text
    assert "01–08" in text          # rango de PNGs = total real de la muestra
    assert "seed=43" not in text
    assert "01–24" not in text


def test_readme_con_defaults_describe_24_imagenes():
    text = readme_text(seed=43, n_violators=12, n_compliant=12)
    assert "seed=43" in text
    assert "12 imágenes con ≥1 violador" in text
    assert "12 solo conformes" in text
    assert "01–24" in text


# ---------------------------------------------------------------- render

def test_render_draws_boxes_with_stratum_colors():
    img = Image.new("RGB", (200, 200), (128, 128, 128))
    persons = [
        _rec("a.jpg", False, bbox=(10, 10, 90, 150)),   # violador → rojo
        _rec("a.jpg", True, bbox=(110, 10, 190, 150)),  # conforme → verde
    ]
    bare_heads = [[20, 12, 40, 30]]
    out = render_audit_image(img, persons, bare_heads)
    assert out.size == (200, 200)
    assert out.getpixel((10, 80)) == COLOR_VIOLATOR    # borde izq persona violadora
    assert out.getpixel((190, 80)) == COLOR_COMPLIANT  # borde der persona conforme
    assert out.getpixel((30, 30)) == COLOR_BARE_HEAD   # borde inferior bare_head


def test_render_does_not_mutate_input_image():
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    render_audit_image(img, [_rec("a.jpg", False, bbox=(10, 10, 90, 90))], [])
    assert img.getpixel((10, 50)) == (128, 128, 128)


def test_render_without_annotations_returns_copy():
    img = Image.new("RGB", (50, 50), (10, 10, 10))
    out = render_audit_image(img, [], [])
    assert out.size == (50, 50)
    assert out.getpixel((25, 25)) == (10, 10, 10)


# ---------------------------------------------------------------- artefactos reales

@needs_artifacts
def test_real_gt_sample_is_24_stratified_and_deterministic():
    gt = json.loads(PERSON_GT.read_text())
    by_img = group_records_by_image(gt["records"])
    viol, conf = stratify_images(by_img)
    s1 = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=43)
    s2 = sample_audit_images(viol, conf, n_violators=12, n_compliant=12, seed=43)
    assert s1 == s2
    assert len(s1) == 24
    assert sum(1 for f in s1 if f in set(viol)) == 12
    assert sum(1 for f in s1 if f in set(conf)) == 12
    # todas las muestreadas pertenecen al GT curado
    assert all(f in by_img for f in s1)
