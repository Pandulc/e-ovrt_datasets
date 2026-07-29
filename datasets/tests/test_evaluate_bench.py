"""Denominador de recall CR-01 en evaluate_bench.py (doc 75 §2.5 del repo docs).

Bug del denominador gemelo: `evaluate_cr01()` recibía `images_by_filename` y no lo
usaba — el denominador era TODO el person_gt, aunque el run no hubiera procesado
esas imágenes o el GT tuviera imágenes fuera del bench evaluado. El denominador
correcto son los violadores **evaluables**: en imágenes del bench Y cubiertas por
el run (mismo criterio que restrict_gt_to_detections del CLI del media-plane).
"""
from bench.evaluate_bench import evaluate_cr01


def _violador(file_name: str, person_bbox: list[float]) -> dict:
    return {"file_name": file_name, "person_bbox": person_bbox,
            "has_helmet": False, "has_vest": True}


def _det_bare_head_en_cabeza(person_bbox: list[float]) -> dict:
    """Detección bare_head cuyo centro cae en el head_region (tercio superior)."""
    x0, y0, x1, _ = person_bbox
    cx, cy = (x0 + x1) / 2, y0 + 10
    return {"prompt_id": "bare_head", "confidence": 0.9,
            "bbox_xyxy": [cx - 5, cy - 5, cx + 5, cy + 5]}


def test_denominador_se_restringe_a_las_imagenes_cubiertas_por_el_run():
    """GT: 4 violadoras en 2 imágenes; el run solo cubre img_a → denominador 2, no 4."""
    person_gt = [
        _violador("img_a.jpg", [0, 0, 100, 200]),
        _violador("img_a.jpg", [200, 0, 300, 200]),
        _violador("img_b.jpg", [0, 0, 100, 200]),
        _violador("img_b.jpg", [200, 0, 300, 200]),
    ]
    images_by_filename = {"img_a.jpg": {"id": 1}, "img_b.jpg": {"id": 2}}
    # El run procesó SOLO img_a (una detección que matchea a la primera persona).
    detections = {"img_a.jpg": [_det_bare_head_en_cabeza([0, 0, 100, 200])]}

    r = evaluate_cr01(person_gt, detections, images_by_filename, iou_threshold=0.5)
    assert r["n_violators"] == 2  # solo las evaluables, no las 4 del GT global
    assert r["n_detected"] == 1
    assert r["cr01_recall"] == 0.5


def test_imagen_del_run_sin_detecciones_sigue_contando_en_el_denominador():
    """Cubierta por el run != detectada: un evento con 0 detecciones mantiene la imagen
    en el denominador (miss real), no la excluye."""
    person_gt = [
        _violador("img_a.jpg", [0, 0, 100, 200]),
        _violador("img_b.jpg", [0, 0, 100, 200]),
    ]
    images_by_filename = {"img_a.jpg": {"id": 1}, "img_b.jpg": {"id": 2}}
    # load_detections crea la clave aunque el evento traiga 0 detecciones.
    detections = {"img_a.jpg": [_det_bare_head_en_cabeza([0, 0, 100, 200])],
                  "img_b.jpg": []}

    r = evaluate_cr01(person_gt, detections, images_by_filename, iou_threshold=0.5)
    assert r["n_violators"] == 2
    assert r["n_detected"] == 1
    assert r["cr01_recall"] == 0.5


def test_gt_fuera_del_bench_coco_queda_excluido_del_denominador():
    """Gemelo del riesgo person_gt histórico vs bench curado: un violador en una
    imagen que NO está en el COCO evaluado no cuenta, aunque el run la haya cubierto."""
    person_gt = [
        _violador("img_a.jpg", [0, 0, 100, 200]),
        _violador("img_excluida.jpg", [0, 0, 100, 200]),  # no está en el bench
    ]
    images_by_filename = {"img_a.jpg": {"id": 1}}
    detections = {"img_a.jpg": [_det_bare_head_en_cabeza([0, 0, 100, 200])],
                  "img_excluida.jpg": [_det_bare_head_en_cabeza([0, 0, 100, 200])]}

    r = evaluate_cr01(person_gt, detections, images_by_filename, iou_threshold=0.5)
    assert r["n_violators"] == 1
    assert r["n_detected"] == 1
    assert r["cr01_recall"] == 1.0


def test_sin_violadoras_evaluables_no_define_recall():
    person_gt = [_violador("img_b.jpg", [0, 0, 100, 200])]
    images_by_filename = {"img_a.jpg": {"id": 1}, "img_b.jpg": {"id": 2}}
    detections = {"img_a.jpg": []}  # el run no cubrió img_b

    r = evaluate_cr01(person_gt, detections, images_by_filename, iou_threshold=0.5)
    assert r["cr01_recall"] is None
    assert r["n_violators"] == 0
