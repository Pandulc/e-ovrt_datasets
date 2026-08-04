"""E-HYB Fase 1 (Nivel A, offline) — fusion pre-registrada de doc 12 §4.

Dual-run (§4.1): las señales de E-HYB son bit a bit las de las corridas E-IND y
E-DIR ya hechas; toda diferencia observada es atribuible SOLO a la funcion de
fusion. Nada de inferencia nueva.

Gating (§4.2): una prediccion E-DIR solo aporta si matchea (IoU>=0.5) con una
persona DETECTADA — evita que un FP suelto sin persona dispare evidencia.

-or (§4.3): union gateada. -and NO cambia quien queda marcado a nivel persona
(E-IND es la señal primaria; su efecto es acelerar la confirmacion, visible recien
en Nivel B): lo que SI se mide en Fase 1 es la tasa de corroboracion sobre TPs vs
sobre FPs de E-IND — si corrobora mas a los aciertos que a los errores, acelerar
por corroboracion es seguro.
"""
import pytest

from bench.fuse_ehyb import (
    corroboration_split,
    fuse_or,
    gate_by_person,
)


def _p(bbox, conf=0.9):
    return {"bbox_xyxy": list(bbox), "confidence": conf}


# ---------------------------------------------------------------------------
# Gating por persona (doc 12 §4.2)
# ---------------------------------------------------------------------------

def test_gating_conserva_la_prediccion_que_solapa_una_persona_detectada():
    edir = [_p([0, 0, 100, 200])]
    personas = [[2, 2, 98, 198]]
    assert gate_by_person(edir, personas) == edir


def test_gating_descarta_la_prediccion_sin_persona():
    """Un FP suelto (sin persona detectada) no puede aportar evidencia."""
    edir = [_p([500, 500, 600, 700])]
    personas = [[0, 0, 100, 200]]
    assert gate_by_person(edir, personas) == []


def test_gating_sin_personas_detectadas_descarta_todo():
    assert gate_by_person([_p([0, 0, 10, 10])], []) == []


# ---------------------------------------------------------------------------
# E-HYB-or: union gateada con dedupe
# ---------------------------------------------------------------------------

def test_or_agrega_la_prediccion_edir_de_una_persona_que_eind_no_marco():
    eind = [_p([0, 0, 100, 200])]
    edir_gated = [_p([300, 0, 400, 200], conf=0.5)]
    fused = fuse_or(eind, edir_gated)
    assert len(fused) == 2


def test_or_no_duplica_la_misma_persona():
    """Si ambos marcan a la misma persona, la fusion emite UNA prediccion.

    Sin dedupe, el segundo box quedaria sin persona libre en el matching 1:1 y
    contaria FP: la fusion se penalizaria a si misma por estar de acuerdo.
    """
    eind = [_p([0, 0, 100, 200], conf=0.8)]
    edir_gated = [_p([5, 5, 95, 195], conf=0.6)]
    fused = fuse_or(eind, edir_gated)
    assert fused == eind  # se queda la de E-IND (señal primaria, box de persona)


def test_or_con_edir_vacio_es_eind():
    eind = [_p([0, 0, 100, 200])]
    assert fuse_or(eind, []) == eind


def test_or_con_eind_vacio_es_edir_gateado():
    edir_gated = [_p([0, 0, 100, 200])]
    assert fuse_or([], edir_gated) == edir_gated


# ---------------------------------------------------------------------------
# Corroboracion (la parte de -and medible en Fase 1)
# ---------------------------------------------------------------------------

def test_corroboracion_separa_tp_de_fp():
    gt = [
        {"person_bbox": [0, 0, 100, 200], "has_helmet": False},    # violadora
        {"person_bbox": [300, 0, 400, 200], "has_helmet": True},   # cumplidora
    ]
    eind = [_p([0, 0, 100, 200], conf=0.9),      # TP
            _p([300, 0, 400, 200], conf=0.8)]    # FP (cumplidora marcada)
    # E-DIR corrobora SOLO a la violadora
    edir_gated = [_p([2, 2, 98, 198], conf=0.5)]
    stats = corroboration_split(gt, eind, edir_gated, "has_helmet")
    assert stats["tp_total"] == 1 and stats["tp_corroborated"] == 1
    assert stats["fp_total"] == 1 and stats["fp_corroborated"] == 0


def test_corroboracion_sin_edir_no_corrobora_nada():
    gt = [{"person_bbox": [0, 0, 100, 200], "has_helmet": False}]
    stats = corroboration_split(gt, [_p([0, 0, 100, 200])], [], "has_helmet")
    assert stats["tp_corroborated"] == 0 and stats["tp_total"] == 1


def test_corroboracion_cuenta_fp_sin_persona_del_gt():
    """Una alucinacion de E-IND corroborada por E-DIR es el peor caso de -and:
    aceleraria una alerta sobre nada. Tiene que quedar contada."""
    gt = []
    eind = [_p([0, 0, 100, 200], conf=0.9)]
    edir_gated = [_p([5, 5, 95, 195], conf=0.5)]
    stats = corroboration_split(gt, eind, edir_gated, "has_helmet")
    assert stats["fp_total"] == 1 and stats["fp_corroborated"] == 1
