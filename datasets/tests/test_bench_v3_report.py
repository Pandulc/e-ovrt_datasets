"""Agregado ponderado por n de resultados de evaluate_perception sobre bench_v3.

Doc 62 §2 (repo docs): el criterio pre-registrado de campeón es mAP50 agregado
con desempate recall CR-01. Este módulo NO decide el campeón — solo calcula el
agregado a partir de los eval_perception.json por estrato, ponderando por n_gt
real (no por conteo de imágenes: una clase ausente en un estrato no debe pesar).
"""
from curate.bench_v3_report import weighted_map50, weighted_cr01_recall


def _class_result(name, ap50, n_gt):
    return {"class_name": name, "AP50": ap50, "n_gt": n_gt}


def test_pondera_por_n_gt_no_por_conteo_de_estratos():
    # estrato A: n_gt=100, AP=0.8 | estrato B: n_gt=900, AP=0.4
    # promedio simple daria 0.6; ponderado por n da 0.44
    evals = [
        {"per_class": [_class_result("person", 0.8, 100)]},
        {"per_class": [_class_result("person", 0.4, 900)]},
    ]
    result = weighted_map50(evals, classes=["person"])
    assert abs(result["person"] - 0.44) < 1e-9


def test_ignora_clases_ausentes_ap_none():
    evals = [
        {"per_class": [_class_result("vest", None, 0)]},
        {"per_class": [_class_result("vest", 0.5, 200)]},
    ]
    result = weighted_map50(evals, classes=["vest"])
    assert result["vest"] == 0.5


def test_clase_sin_ningun_gt_en_ningun_estrato_da_none():
    evals = [{"per_class": [_class_result("bare_head", None, 0)]}]
    result = weighted_map50(evals, classes=["bare_head"])
    assert result["bare_head"] is None


def test_recall_cr01_pondera_por_violadores_reales():
    evals = [
        {"cr01_detection_recall": 0.5, "cr01_n_violators": 30},
        {"cr01_detection_recall": 0.2, "cr01_n_violators": 70},
    ]
    r = weighted_cr01_recall(evals)
    assert abs(r - (0.5 * 30 + 0.2 * 70) / 100) < 1e-9
