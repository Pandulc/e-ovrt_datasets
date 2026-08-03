"""Tests del agregador de campañas sobre el banco de clips.

Lo que el agregado tiene que garantizar para que los numeros lleguen al informe
sin trampas:

- los clips NEGATIVOS no entran a precision/recall/F1 (F-EV1: su
  `applicability_state` es `not_applicable`, y promediarlos hundiria el agregado
  con aciertos contados como catastrofes) pero SI al control de falsos positivos;
- los episodios CENSURADOS salen del denominador de recall (A2, doc 57 §6.7);
- las `re_alerts` NO son FP (ADR-011);
- el desglose POR ESCENARIO siempre se emite (limitacion L5 del registry: los
  agregados estan dominados por P1/P2, reportar solo el global engana);
- micro (por episodio) y macro (por clip) se distinguen: con escenarios
  desbalanceados no son lo mismo y el informe tiene que decir cual usa.
"""

import json

import pytest

from bench.aggregate_clip_campaign import aggregate_campaign


def _eval(clip_id, *, expected=1, matched=1, missed=0, censored=0, fp=0,
          re_alerts=0, state="computed", cause=None, t_alert=4200.0,
          ttfd=200.0, sdr=0.8, far=0.0, duration=20000.0):
    return {
        "schema_version": "control.eval.temporal.v1", "scenario_id": clip_id,
        "expected_alerts_count": expected, "matched_alerts_count": matched,
        "missed_alerts_count": missed, "censored_episodes_count": censored,
        "unexpected_alerts_count": fp, "re_alerts_count": re_alerts,
        "sub_threshold_count": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0,
        "applicability_state": state, "applicability_cause": cause,
        "avg_latency_ms_from_episode_start": t_alert, "avg_ttfd_ms": ttfd,
        "avg_sdr": sdr, "far_per_hour": far, "observed_duration_ms": duration,
    }


def _gt(clip_id, *, scenario, conditions=("CR-01",), duration=20000.0):
    return {
        "schema_version": "clip_gt.v2", "clip_id": clip_id, "scenario": scenario,
        "duration_ms": duration, "negative": not conditions,
        "episodes": [{"id": f"ep{i+1}", "condition_id": c, "level": "scene",
                      "source_id": clip_id, "start_ms": 3000.0, "end_ms": 15000.0}
                     for i, c in enumerate(conditions)],
        "sub_threshold_events": [],
    }


def _write(tmp_path, evals, gts):
    ed, gd = tmp_path / "evals", tmp_path / "gt"
    ed.mkdir(); gd.mkdir()
    for c, e in evals.items():
        (ed / f"eval_{c}.json").write_text(json.dumps(e))
    for c, g in gts.items():
        (gd / f"{c}.json").write_text(json.dumps(g))
    return ed, gd


def test_los_negativos_no_entran_a_recall_ni_precision(tmp_path):
    evals = {
        "a_p1_c01": _eval("a_p1_c01"),
        "a_p3_c01": _eval("a_p3_c01", expected=0, matched=0,
                          state="not_applicable", cause="negative_clip_no_episodes",
                          t_alert=None, ttfd=None, sdr=None),
    }
    gts = {"a_p1_c01": _gt("a_p1_c01", scenario="P1"),
           "a_p3_c01": _gt("a_p3_c01", scenario="P3", conditions=())}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["positives"]["clips"] == 1
    assert m["positives"]["recall_micro"] == 1.0
    assert m["negatives"]["clips"] == 1


def test_los_negativos_si_entran_al_control_de_falsos_positivos(tmp_path):
    evals = {"a_p3_c01": _eval("a_p3_c01", expected=0, matched=0, fp=2,
                               state="not_applicable",
                               cause="negative_clip_no_episodes",
                               t_alert=None, ttfd=None, sdr=None, duration=18000.0)}
    # la duracion la toma del GT (fuente de verdad del clip), no del eval
    gts = {"a_p3_c01": _gt("a_p3_c01", scenario="P3", conditions=(), duration=18000.0)}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["negatives"]["false_positives"] == 2
    assert m["negatives"]["observed_ms"] == 18000.0


def test_los_episodios_censurados_salen_del_denominador_de_recall(tmp_path):
    evals = {"a_p1_c01": _eval("a_p1_c01", expected=2, matched=1, censored=1)}
    gts = {"a_p1_c01": _gt("a_p1_c01", scenario="P1", conditions=("CR-01", "CR-01"))}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["positives"]["episodes_evaluable"] == 1
    assert m["positives"]["recall_micro"] == 1.0


def test_las_re_alerts_no_cuentan_como_falsos_positivos(tmp_path):
    evals = {"a_p1_c01": _eval("a_p1_c01", fp=0, re_alerts=3)}
    gts = {"a_p1_c01": _gt("a_p1_c01", scenario="P1")}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["positives"]["precision_micro"] == 1.0
    assert m["positives"]["re_alerts"] == 3


def test_emite_desglose_por_escenario(tmp_path):
    evals = {"a_p1_c01": _eval("a_p1_c01"),
             "a_p7_c01": _eval("a_p7_c01", matched=0, missed=1, fp=1)}
    gts = {"a_p1_c01": _gt("a_p1_c01", scenario="P1"),
           "a_p7_c01": _gt("a_p7_c01", scenario="P7")}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["by_scenario"]["P1"]["recall"] == 1.0
    assert m["by_scenario"]["P7"]["recall"] == 0.0
    assert m["by_scenario"]["P7"]["false_positives"] == 1


def test_emite_desglose_por_condicion_desde_el_GT(tmp_path):
    """La condicion sale de los episodios del GT, no del nombre del clip."""
    evals = {"a_p6_c01": _eval("a_p6_c01", expected=2, matched=2)}
    gts = {"a_p6_c01": _gt("a_p6_c01", scenario="P6", conditions=("CR-01", "CR-02"))}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["by_condition"]["CR-01"]["episodes"] == 1
    assert m["by_condition"]["CR-02"]["episodes"] == 1


def test_distingue_micro_de_macro(tmp_path):
    """Con escenarios desbalanceados micro != macro; el informe debe elegir."""
    evals = {"a_p1_c01": _eval("a_p1_c01", expected=3, matched=3),
             "a_p7_c01": _eval("a_p7_c01", expected=1, matched=0, missed=1)}
    gts = {"a_p1_c01": _gt("a_p1_c01", scenario="P1",
                           conditions=("CR-01", "CR-01", "CR-01")),
           "a_p7_c01": _gt("a_p7_c01", scenario="P7")}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["positives"]["recall_micro"] == 0.75      # 3 de 4 episodios
    assert m["positives"]["recall_macro"] == 0.5       # media de 1.0 y 0.0


def test_far_por_hora_solo_con_clips_soak(tmp_path):
    """L1: sin negativos >=5 min el denominador no existe (doc 57 §3.2 G1)."""
    evals = {"a_p3_c01": _eval("a_p3_c01", expected=0, matched=0, fp=1,
                               state="not_applicable",
                               cause="negative_clip_no_episodes",
                               t_alert=None, ttfd=None, sdr=None, duration=18000.0)}
    gts = {"a_p3_c01": _gt("a_p3_c01", scenario="P3", conditions=(), duration=18000.0)}
    m = aggregate_campaign(*_write(tmp_path, evals, gts))

    assert m["negatives"]["far_per_hour"] is None
    assert "soak" in m["negatives"]["far_basis"].lower()


def test_rechaza_un_eval_sin_su_GT(tmp_path):
    evals = {"a_p1_c01": _eval("a_p1_c01")}
    gts = {}
    with pytest.raises(ValueError, match="sin GT"):
        aggregate_campaign(*_write(tmp_path, evals, gts))
