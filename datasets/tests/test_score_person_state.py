"""Scoring de estado por persona — Fase D, Fase 1 (Nivel A).

Pre-registro `nucleo/04` §7 Fase 1: se puntua el estado "sin EPP" a nivel PERSONA
contra has_helmet/has_vest, con umbrales calibrados en la mitad A y todo lo reportado
saliendo de la mitad B.

Las dos estrategias predicen el mismo objeto (persona en violacion) por caminos
distintos:
  E-IND — se aplica `spatial_absence` offline sobre las detecciones positivas
          (person + helmet/vest), replicando la region del pattern set desplegado.
  E-DIR — la deteccion de la variante ES la prediccion; se matchea por IoU contra
          la persona del GT.

Ambas se puntuan sobre EL MISMO conjunto de personas del GT: una persona que ningun
detector encontro cuenta como fallo para las dos. Ese es el numero honesto de
percepcion punta a punta.
"""
import pytest

from bench.score_person_state import (
    bootstrap_ci,
    match_predictions_to_gt,
    predict_edir,
    predict_eind,
    prf1,
    region_bbox,
    stratified_halves,
    sweep_best_threshold,
)

# Region CR-01 del pattern set desplegado cr01_cr02_v2.
REGION_CR01 = {"y_min_ratio": 0.0, "y_max_ratio": 0.45, "x_margin_ratio": 0.12}
REGION_CR02 = {"y_min_ratio": 0.25, "y_max_ratio": 0.85, "x_margin_ratio": 0.08}


def _det(label, bbox, conf=0.9, prompt_id=None):
    return {"label": label, "prompt_id": prompt_id or label, "confidence": conf,
            "bbox_xyxy": list(bbox)}


# ---------------------------------------------------------------------------
# Region: misma aritmetica que el control-plane
# ---------------------------------------------------------------------------

def test_region_replica_la_del_control_plane():
    # persona 100x200 en el origen; upper_body 0..0.45 con margen 0.12
    assert region_bbox([0, 0, 100, 200], REGION_CR01) == pytest.approx([12.0, 0.0, 88.0, 90.0])


def test_region_torso_cr02():
    assert region_bbox([0, 0, 100, 200], REGION_CR02) == pytest.approx([8.0, 50.0, 92.0, 170.0])


# ---------------------------------------------------------------------------
# E-IND: spatial_absence offline
# ---------------------------------------------------------------------------

def test_eind_persona_con_casco_en_la_region_no_es_violacion():
    dets = [_det("person", [0, 0, 100, 200]), _det("helmet", [40, 10, 60, 30])]
    preds = predict_eind(dets, "helmet", REGION_CR01, person_conf=0.35, evidence_conf=0.25)
    assert preds == []


def test_eind_persona_sin_casco_es_violacion():
    dets = [_det("person", [0, 0, 100, 200])]
    preds = predict_eind(dets, "helmet", REGION_CR01, person_conf=0.35, evidence_conf=0.25)
    assert len(preds) == 1
    assert preds[0]["bbox_xyxy"] == [0, 0, 100, 200]


def test_eind_casco_fuera_de_la_region_no_cubre():
    """Un casco al pie de la persona no la cubre: la region es lo que hace la asociacion."""
    dets = [_det("person", [0, 0, 100, 200]), _det("helmet", [40, 180, 60, 195])]
    preds = predict_eind(dets, "helmet", REGION_CR01, person_conf=0.35, evidence_conf=0.25)
    assert len(preds) == 1


def test_eind_respeta_el_umbral_de_la_evidencia():
    """Un casco por debajo del umbral no cuenta como cobertura -> la persona viola."""
    dets = [_det("person", [0, 0, 100, 200]), _det("helmet", [40, 10, 60, 30], conf=0.20)]
    preds = predict_eind(dets, "helmet", REGION_CR01, person_conf=0.35, evidence_conf=0.25)
    assert len(preds) == 1


def test_eind_respeta_el_umbral_del_sujeto():
    dets = [_det("person", [0, 0, 100, 200], conf=0.30)]
    preds = predict_eind(dets, "helmet", REGION_CR01, person_conf=0.35, evidence_conf=0.25)
    assert preds == []


def test_eind_usa_vest_para_cr02():
    dets = [_det("person", [0, 0, 100, 200]), _det("vest", [40, 100, 60, 130])]
    assert predict_eind(dets, "vest", REGION_CR02, 0.35, 0.25) == []
    assert len(predict_eind(dets, "helmet", REGION_CR01, 0.35, 0.25)) == 1


# ---------------------------------------------------------------------------
# E-DIR: la deteccion de la variante ES la prediccion
# ---------------------------------------------------------------------------

def test_edir_toma_solo_su_variante():
    dets = [_det("cr01_neg", [0, 0, 100, 200], prompt_id="cr01_neg"),
            _det("cr02_neg", [5, 5, 90, 190], prompt_id="cr02_neg")]
    preds = predict_edir(dets, "cr01_neg", conf=0.30)
    assert len(preds) == 1
    assert preds[0]["bbox_xyxy"] == [0, 0, 100, 200]


def test_edir_respeta_el_umbral():
    dets = [_det("cr01_neg", [0, 0, 100, 200], conf=0.25, prompt_id="cr01_neg")]
    assert predict_edir(dets, "cr01_neg", conf=0.30) == []


# ---------------------------------------------------------------------------
# Matching prediccion <-> persona del GT
# ---------------------------------------------------------------------------

def test_persona_violadora_detectada_es_true_positive():
    gt = [{"person_bbox": [0, 0, 100, 200], "has_helmet": False}]
    preds = [{"bbox_xyxy": [2, 2, 98, 198], "confidence": 0.9}]
    res = match_predictions_to_gt(gt, preds, "has_helmet", iou_thr=0.5)
    assert res["tp"] == 1 and res["fn"] == 0 and res["fp"] == 0


def test_persona_violadora_no_detectada_es_false_negative():
    gt = [{"person_bbox": [0, 0, 100, 200], "has_helmet": False}]
    res = match_predictions_to_gt(gt, [], "has_helmet", iou_thr=0.5)
    assert res["fn"] == 1 and res["tp"] == 0


def test_persona_cumplidora_marcada_es_false_positive():
    gt = [{"person_bbox": [0, 0, 100, 200], "has_helmet": True}]
    preds = [{"bbox_xyxy": [2, 2, 98, 198], "confidence": 0.9}]
    res = match_predictions_to_gt(gt, preds, "has_helmet", iou_thr=0.5)
    assert res["fp"] == 1 and res["tp"] == 0


def test_prediccion_sin_persona_de_gt_tambien_es_false_positive():
    """Una alucinacion donde no hay nadie anotado no puede salir gratis."""
    gt = [{"person_bbox": [0, 0, 100, 200], "has_helmet": False}]
    preds = [{"bbox_xyxy": [2, 2, 98, 198], "confidence": 0.9},
             {"bbox_xyxy": [500, 500, 600, 700], "confidence": 0.9}]
    res = match_predictions_to_gt(gt, preds, "has_helmet", iou_thr=0.5)
    assert res["tp"] == 1 and res["fp"] == 1


def test_una_prediccion_no_puede_cubrir_dos_personas():
    """Matching 1:1 — si no, una caja grande 'acierta' toda una multitud."""
    gt = [{"person_bbox": [0, 0, 100, 200], "has_helmet": False},
          {"person_bbox": [10, 10, 105, 205], "has_helmet": False}]
    preds = [{"bbox_xyxy": [0, 0, 100, 200], "confidence": 0.9}]
    res = match_predictions_to_gt(gt, preds, "has_helmet", iou_thr=0.5)
    assert res["tp"] == 1 and res["fn"] == 1


def test_iou_por_debajo_del_umbral_no_matchea():
    gt = [{"person_bbox": [0, 0, 100, 200], "has_helmet": False}]
    preds = [{"bbox_xyxy": [90, 190, 200, 400], "confidence": 0.9}]
    res = match_predictions_to_gt(gt, preds, "has_helmet", iou_thr=0.5)
    assert res["fn"] == 1 and res["fp"] == 1


def test_personas_marcadas_ambiguas_pueden_excluirse():
    """Sensibilidad de la atribucion de CR-02 (doc 83): con y sin las ambiguas."""
    gt = [{"person_bbox": [0, 0, 100, 200], "has_vest": False,
           "vest_attribution_ambiguous": True}]
    con = match_predictions_to_gt(gt, [], "has_vest", iou_thr=0.5)
    sin = match_predictions_to_gt(gt, [], "has_vest", iou_thr=0.5, skip_ambiguous_vest=True)
    assert con["fn"] == 1
    assert sin["fn"] == 0 and sin["n_gt_positive"] == 0


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------

def test_prf1_basico():
    m = prf1({"tp": 8, "fp": 2, "fn": 2})
    assert m["precision"] == pytest.approx(0.8)
    assert m["recall"] == pytest.approx(0.8)
    assert m["f1"] == pytest.approx(0.8)


def test_prf1_sin_predicciones_no_inventa_precision_1():
    """0 predicciones no es precision perfecta: es precision indefinida."""
    m = prf1({"tp": 0, "fp": 0, "fn": 5})
    assert m["precision"] is None
    assert m["recall"] == 0.0
    assert m["f1"] == 0.0


def test_prf1_sin_positivos_en_el_gt_deja_recall_indefinido():
    m = prf1({"tp": 0, "fp": 3, "fn": 0})
    assert m["recall"] is None
    assert m["precision"] == 0.0


# ---------------------------------------------------------------------------
# Particion calib/test
# ---------------------------------------------------------------------------

def test_mitades_estratificadas_son_disjuntas_y_cubren_todo():
    items = [(f"img{i}", "pos" if i % 3 == 0 else "neg") for i in range(60)]
    a, b = stratified_halves(items, seed=7)
    assert set(a) & set(b) == set()
    assert len(set(a) | set(b)) == 60


def test_mitades_conservan_la_proporcion_del_estrato():
    items = [(f"img{i}", "pos" if i % 3 == 0 else "neg") for i in range(60)]
    a, b = stratified_halves(items, seed=7)
    pos = {i for i, k in items if k == "pos"}
    assert abs(len(set(a) & pos) - len(set(b) & pos)) <= 1


def test_la_particion_es_determinista():
    items = [(f"img{i}", "pos" if i % 2 else "neg") for i in range(40)]
    assert stratified_halves(items, seed=3) == stratified_halves(items, seed=3)
    assert stratified_halves(items, seed=3) != stratified_halves(items, seed=4)


# ---------------------------------------------------------------------------
# Calibracion de umbral
# ---------------------------------------------------------------------------

def test_sweep_elige_el_umbral_que_maximiza_f1():
    def score_at(thr):
        # F1 maximo en 0.5 por construccion
        return {"f1": 1.0 - abs(thr - 0.5)}
    best = sweep_best_threshold([0.3, 0.4, 0.5, 0.6], score_at)
    assert best["threshold"] == 0.5


def test_sweep_ignora_umbrales_con_f1_indefinido():
    def score_at(thr):
        return {"f1": None} if thr < 0.5 else {"f1": 0.7}
    best = sweep_best_threshold([0.3, 0.4, 0.5, 0.6], score_at)
    assert best["threshold"] == 0.5


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def test_bootstrap_devuelve_intervalo_que_contiene_el_punto():
    unidades = [{"tp": 1, "fp": 0, "fn": 0}] * 80 + [{"tp": 0, "fp": 0, "fn": 1}] * 20
    ci = bootstrap_ci(unidades, "recall", n_iter=200, seed=1)
    assert ci["lo"] <= 0.8 <= ci["hi"]
    assert 0.0 <= ci["lo"] <= ci["hi"] <= 1.0


def test_bootstrap_es_determinista_con_semilla():
    unidades = [{"tp": 1, "fp": 0, "fn": 0}] * 50 + [{"tp": 0, "fp": 1, "fn": 0}] * 50
    assert bootstrap_ci(unidades, "precision", n_iter=100, seed=5) == \
           bootstrap_ci(unidades, "precision", n_iter=100, seed=5)
