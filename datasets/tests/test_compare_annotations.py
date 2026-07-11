"""Kappa de Cohen por ventana de 1 s + deltas de bordes (spec 43 §4.2)."""
import pytest

from videogt.compare_annotations import cohen_kappa, compare, window_states


def _gt(episodes, duration_ms=10000):
    return {"schema_version": "clip_gt.v2", "clip_id": "c", "duration_ms": duration_ms,
            "episodes": episodes, "sub_threshold_events": []}


def _ep(cond, start, end):
    return {"id": "e", "condition_id": cond, "level": "scene",
            "start_ms": start, "end_ms": end, "subjects_in_evidence": 1, "notes": ""}


def test_window_states_muestrea_punto_medio():
    gt = _gt([_ep("CR-01", 1400, 3600)])
    # ventanas [0,1s):midpoint 500→F, [1,2s):1500→T, [2,3s):2500→T, [3,4s):3500→T, resto F
    assert window_states(gt, "CR-01")[:5] == [False, True, True, True, False]
    assert len(window_states(gt, "CR-01")) == 10


def test_cohen_kappa_extremos():
    a = [True, True, False, False]
    assert cohen_kappa(a, a) == 1.0
    assert cohen_kappa(a, [not v for v in a]) < 0
    assert cohen_kappa([True, False], [True, True]) == 0.0


def test_compare_acuerdo_perfecto():
    gt = _gt([_ep("CR-01", 1000, 5000)])
    result = compare(gt, gt)
    assert result["kappa_global"] == 1.0
    assert result["median_abs_dstart_ms"] == 0
    assert result["unpaired_a"] == 0 and result["unpaired_b"] == 0


def test_compare_reporta_deltas_y_desapareados():
    a = _gt([_ep("CR-01", 1000, 5000), _ep("CR-02", 6000, 9000)])
    b = _gt([_ep("CR-01", 1400, 5300)])  # borde corrido, CR-02 no visto
    result = compare(a, b)
    assert result["median_abs_dstart_ms"] == 400
    assert result["median_abs_dend_ms"] == 300
    assert result["unpaired_a"] == 1 and result["unpaired_b"] == 0
    assert result["kappa_global"] < 1.0


# FIX 5 (auditoría 2026-07-11): duration_ms distinto entre los dos GT
# significa que no son del mismo clip preparado (recortes distintos) — antes
# `window_states` truncaba en silencio a la duración de cada GT por
# separado, produciendo un kappa engañoso en vez de fallar ruidosamente.
def test_fix5_duration_ms_distinto_da_error_claro():
    a = _gt([_ep("CR-01", 1000, 5000)], duration_ms=10000)
    b = _gt([_ep("CR-01", 1000, 5000)], duration_ms=8000)
    with pytest.raises(ValueError, match="duration_ms"):
        compare(a, b)
