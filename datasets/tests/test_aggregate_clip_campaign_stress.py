"""Stress de COMPOSICIÓN EXTREMA del agregador de campañas (doc 111 §6).

Por qué existe este archivo aparte de `test_aggregate_clip_campaign.py`: el bug de
`far_per_hour` del 2026-08-09 **pasó todos los tests existentes**. No fallaba la
aritmética de ninguna métrica aislada; fallaba la COMPOSICIÓN — el numerador salía
de un subconjunto de clips (todos los negativos) y el denominador de otro (solo los
soak). Con 2 negativos la distorsión era 1,2× e invisible; con 9 saltó a 7×.

La lección es que los tests puntuales verifican fórmulas y el banco real verifica
una sola composición. Lo que no estaba cubierto es el espacio entre las dos: qué
pasa con 1 clip, con 0 negativos, con 0 soak, con duraciones que difieren 60×.

Este archivo cubre ese espacio de dos formas complementarias:

1. **Composiciones extremas puntuales**, cada una con el valor esperado calculado A
   MANO en el propio test (nunca derivado del código bajo prueba).
2. **Invariantes property-style** que se comprueban sobre TODAS las composiciones:
   (a) toda tasa reconstruye su numerador desde SU propio denominador declarado
       — el invariante que el bug violaba;
   (b) los conteos por clip suman al agregado;
   (c) las micro-métricas son consistentes con los conteos crudos;
   (d) `None` donde no es computable, nunca un 0.0 que parezca medido — y su
       recíproco: 0.0 donde SÍ se midió cero, nunca un `None` que parezca faltante.
"""

import json

import pytest

from bench.aggregate_clip_campaign import aggregate_campaign
from bench.score_person_state import prf1

HORA_MS = 3_600_000.0


# ---------------------------------------------------------------------------
# Constructor de composiciones
# ---------------------------------------------------------------------------

def _clip(cid, *, scenario="P1", conditions=("CR-01",), duration=20_000.0,
          expected=None, matched=0, censored=0, fp=0, re_alerts=0,
          sub_threshold=0, t_alert=4200.0, ttfd=200.0, sdr=0.8):
    """(gt, eval) de un clip. `expected=None` -> tantos episodios como condiciones.

    Refleja la invariante verificada contra el banco real (416/416 evals):
    `expected_alerts_count` == cantidad de episodios del GT.
    """
    if expected is None:
        expected = len(conditions)
    negativo = expected == 0
    gt = {
        "schema_version": "clip_gt.v2", "clip_id": cid, "scenario": scenario,
        "duration_ms": duration, "negative": negativo,
        "episodes": [{"id": f"{cid}_ep{i + 1}", "condition_id": conditions[i % len(conditions)],
                      "level": "scene", "source_id": cid,
                      "start_ms": 3000.0, "end_ms": 15000.0}
                     for i in range(expected)],
        "sub_threshold_events": [],
    }
    ev = {
        "schema_version": "control.eval.temporal.v1", "scenario_id": cid,
        "expected_alerts_count": expected, "matched_alerts_count": matched,
        "missed_alerts_count": max(0, expected - censored - matched),
        "censored_episodes_count": censored, "unexpected_alerts_count": fp,
        "re_alerts_count": re_alerts, "sub_threshold_count": sub_threshold,
        "precision": 0.0, "recall": 0.0, "f1": 0.0,
        "applicability_state": "not_applicable" if negativo else "computed",
        "applicability_cause": "negative_clip_no_episodes" if negativo else None,
        "avg_latency_ms_from_episode_start": None if negativo else t_alert,
        "avg_ttfd_ms": None if negativo else ttfd,
        "avg_sdr": None if negativo else sdr,
        "far_per_hour": 0.0, "observed_duration_ms": duration,
    }
    return gt, ev


def _run(tmp_path, clips):
    ed, gd = tmp_path / "evals", tmp_path / "gt"
    ed.mkdir(exist_ok=True); gd.mkdir(exist_ok=True)
    for gt, ev in clips:
        (gd / f"{gt['clip_id']}.json").write_text(json.dumps(gt))
        (ed / f"eval_{gt['clip_id']}.json").write_text(json.dumps(ev))
    return aggregate_campaign(str(ed), str(gd), None)


def _neg(cid, *, duration, fp=0, re_alerts=0, scenario="P3"):
    return _clip(cid, scenario=scenario, conditions=(), expected=0,
                 duration=duration, fp=fp, re_alerts=re_alerts)


# ---------------------------------------------------------------------------
# 1. Un solo clip
# ---------------------------------------------------------------------------

def test_un_solo_clip_positivo(tmp_path):
    """A mano: 2 episodios evaluables, 1 acertado, 1 FP."""
    m = _run(tmp_path, [_clip("solo", conditions=("CR-01", "CR-01"),
                              expected=2, matched=1, fp=1)])
    p, n = m["positives"], m["negatives"]

    assert m["clips_total"] == 1
    assert p["clips"] == 1 and p["episodes_total"] == 2
    assert p["episodes_evaluable"] == 2
    assert p["recall_micro"] == 0.5              # 1/2
    assert p["precision_micro"] == 0.5           # 1/(1+1)
    assert p["f1_micro"] == 0.5                  # 2*.5*.5/(.5+.5)
    assert p["recall_macro"] == 0.5              # un solo clip: micro == macro
    # sin negativos no hay control de FP: None, jamas un 0.0 que parezca medido
    assert n["clips"] == 0
    assert n["far_per_hour"] is None
    assert n["far_per_hour_all_negatives"] is None


def test_un_solo_clip_negativo_corto(tmp_path):
    """A mano: 18 s = 0,005 h; 2 FP -> 400 FA/h en la base informativa.

    400 FA/h es justamente el numero que la base declarada se niega a publicar:
    extrapolar 2 FP de 18 segundos a una hora es aritmetica, no medicion.
    """
    m = _run(tmp_path, [_neg("corto", duration=18_000.0, fp=2)])
    p, n = m["positives"], m["negatives"]

    assert p["clips"] == 0
    assert n["clips"] == 1 and n["false_positives"] == 2
    assert n["observed_ms"] == 18_000.0
    assert n["soak_clips"] == 0 and n["soak_ms"] == 0
    assert n["far_per_hour"] is None                       # no hay soak
    assert n["far_per_hour_all_negatives"] == 400.0        # 2 / 0,005 h


def test_un_solo_clip_soak(tmp_path):
    """A mano: 6 min = 0,1 h; 3 FP -> 30 FA/h. Con todo el tiempo negativo en
    soak, las dos bases tienen que COINCIDIR (mismo subconjunto)."""
    m = _run(tmp_path, [_neg("soak", duration=360_000.0, fp=3)])
    n = m["negatives"]

    assert n["soak_clips"] == 1 and n["soak_false_positives"] == 3
    assert n["far_per_hour"] == 30.0
    assert n["far_per_hour_all_negatives"] == 30.0
    assert n["far_per_hour"] == n["far_per_hour_all_negatives"]


# ---------------------------------------------------------------------------
# 2-4. Composiciones degeneradas
# ---------------------------------------------------------------------------

def test_todos_negativos_las_metricas_de_positivos_son_none_no_cero(tmp_path):
    """Sin un solo clip positivo, recall/precision/F1 no valen 0: no existen.

    Un 0.0 aca se promedia despues con campanas reales y hunde el agregado; es
    F-EV1 otra vez, en la escala de la campana entera.
    """
    m = _run(tmp_path, [_neg("n1", duration=30_000.0, fp=1),
                        _neg("n2", duration=45_000.0),
                        _neg("n3", duration=360_000.0, fp=2)])
    p = m["positives"]

    assert p["clips"] == 0
    assert p["episodes_total"] == 0 and p["episodes_evaluable"] == 0
    for k in ("recall_micro", "precision_micro", "f1_micro", "recall_macro",
              "t_alert_system_ms", "ttfd_ms", "sdr"):
        assert p[k] is None, f"{k} deberia ser None y vale {p[k]!r}"
    # el control de FP si es computable, y con su propia base
    assert m["negatives"]["far_per_hour"] == 20.0           # 2 FP / 0,1 h (solo el soak)


def test_todos_positivos_far_es_none_no_cero(tmp_path):
    """Sin negativos, FAR no es 0 FA/h: es no medible. Un 0.0 aqui seria la
    afirmacion (falsa) de que se observo tiempo sin riesgo y no hubo alertas."""
    m = _run(tmp_path, [_clip("p1", matched=1), _clip("p2", matched=0, fp=2)])
    n = m["negatives"]

    assert n["clips"] == 0 and n["false_positives"] == 0 and n["observed_ms"] == 0
    assert n["far_per_hour"] is None
    assert n["far_per_hour_all_negatives"] is None
    # los FP de clips POSITIVOS no se cuelan al control de negativos
    assert m["positives"]["false_positives"] == 2


def test_cero_soak_con_negativos_presentes(tmp_path):
    """A mano: 3 negativos de 60 s = 180 s = 0,05 h, 3 FP -> 60 FA/h informativo.
    La base declarada queda None porque ningun negativo llega a 5 min."""
    m = _run(tmp_path, [_neg("c1", duration=60_000.0, fp=1),
                        _neg("c2", duration=60_000.0, fp=0),
                        _neg("c3", duration=60_000.0, fp=2)])
    n = m["negatives"]

    assert n["clips"] == 3 and n["false_positives"] == 3
    assert n["soak_clips"] == 0 and n["soak_ms"] == 0
    assert n["far_per_hour"] is None
    assert n["far_per_hour_all_negatives"] == 60.0
    assert "soak" in n["far_basis"].lower()


# ---------------------------------------------------------------------------
# 5. El invariante que el bug violaba, con >= 2 soak
# ---------------------------------------------------------------------------

def test_dos_soak_numerador_y_denominador_del_mismo_subconjunto(tmp_path):
    """A mano, con 2 soak y 3 negativos cortos:

      soak:   360 s (2 FP) + 600 s (4 FP) = 6 FP en 960 s = 0,266667 h -> 22,5 FA/h
      todos:  6 + 3*5 = 21 FP en 1050 s = 0,291667 h                   -> 72,0 FA/h
      bug:    21 FP (todos) / 0,266667 h (solo soak)                   -> 78,75 FA/h

    El valor del bug (78,75) esta ENTRE los dos legitimos, que es exactamente por
    que sobrevivio: no es absurdo a simple vista, solo esta mal compuesto.
    """
    m = _run(tmp_path, [
        _neg("soak_a", duration=360_000.0, fp=2),
        _neg("soak_b", duration=600_000.0, fp=4),
        _neg("corto_1", duration=30_000.0, fp=5),
        _neg("corto_2", duration=30_000.0, fp=5),
        _neg("corto_3", duration=30_000.0, fp=5),
    ])
    n = m["negatives"]

    assert n["clips"] == 5 and n["soak_clips"] == 2
    assert n["false_positives"] == 21 and n["soak_false_positives"] == 6
    assert n["soak_ms"] == 960_000.0 and n["observed_ms"] == 1_050_000.0
    assert n["far_per_hour"] == 22.5
    assert n["far_per_hour_all_negatives"] == 72.0
    assert n["far_per_hour"] != pytest.approx(78.75, abs=0.01), "regresion del bug"


# ---------------------------------------------------------------------------
# 6. Duraciones muy heterogeneas
# ---------------------------------------------------------------------------

def test_duraciones_heterogeneas_6s_contra_6min(tmp_path):
    """A mano: 6 s (1 FP) + 360 s (1 FP).

      declarada  = 1 FP / 0,1 h                = 10,0 FA/h
      informativa= 2 FP / (366 s = 0,101667 h) = 19,672131 FA/h

    El clip de 6 s solo extrapolaria a 600 FA/h. La base declarada no lo mira; la
    informativa lo diluye. Ninguna de las dos mezcla subconjuntos.
    """
    m = _run(tmp_path, [_neg("micro", duration=6_000.0, fp=1),
                        _neg("soak", duration=360_000.0, fp=1)])
    n = m["negatives"]

    assert n["far_per_hour"] == 10.0
    assert n["far_per_hour_all_negatives"] == pytest.approx(19.672131, abs=1e-6)
    assert n["far_per_hour"] < n["far_per_hour_all_negatives"]


# ---------------------------------------------------------------------------
# 7. re_alerts (ADR-011)
# ---------------------------------------------------------------------------

def test_re_alerts_masivas_no_son_fp_en_ninguna_metrica(tmp_path):
    """ADR-011: el motor emite en cada confirmacion; las re-alertas no son FP.

    Con 50 re_alerts en el positivo y 20 en el soak, precision debe seguir en 1.0 y
    FAR en 0.0 MEDIDO (hay 6 min de negativo observados y cero FP) — no en None.
    """
    m = _run(tmp_path, [_clip("p1", matched=1, fp=0, re_alerts=50),
                        _neg("soak", duration=360_000.0, fp=0, re_alerts=20)])
    p, n = m["positives"], m["negatives"]

    assert p["precision_micro"] == 1.0 and p["re_alerts"] == 50
    assert p["f1_micro"] == 1.0
    assert n["false_positives"] == 0
    assert n["far_per_hour"] == 0.0          # cero MEDIDO
    assert n["far_per_hour"] is not None
    assert n["far_per_hour_all_negatives"] == 0.0


# ---------------------------------------------------------------------------
# 8. Censurados mezclados con evaluables
# ---------------------------------------------------------------------------

def test_censurados_mezclados_con_evaluables(tmp_path):
    """A mano:
      A: 3 esperados, 2 censurados, 1 acertado -> 1 evaluable, recall 1,0
      B: 2 esperados, 0 censurados, 1 acertado -> 2 evaluables, recall 0,5
      C: 2 esperados, 2 censurados, 0 acertados -> 0 evaluables, recall None

      micro = 2/3 = 0,666667 ; macro = media(1,0 ; 0,5) = 0,75  (C queda FUERA)
    """
    m = _run(tmp_path, [
        _clip("A", conditions=("CR-01",) * 3, expected=3, censored=2, matched=1),
        _clip("B", conditions=("CR-01",) * 2, expected=2, censored=0, matched=1),
        _clip("C", conditions=("CR-01",) * 2, expected=2, censored=2, matched=0),
    ])
    p = m["positives"]
    por_clip = {c["clip_id"]: c for c in m["by_clip"]}

    assert p["episodes_total"] == 7
    assert p["episodes_censored"] == 4
    assert p["episodes_evaluable"] == 3
    assert p["recall_micro"] == pytest.approx(0.666667, abs=1e-6)
    assert p["recall_macro"] == 0.75
    assert por_clip["A"]["recall"] == 1.0
    assert por_clip["B"]["recall"] == 0.5
    assert por_clip["C"]["recall"] is None       # 0 evaluables: no es 0.0
    # y la macro declara sobre cuantos clips se calculo (C no entra)
    assert p["recall_macro_n"] == 2


# ---------------------------------------------------------------------------
# F1: el 0 medido y el None no medible
# ---------------------------------------------------------------------------

def test_f1_micro_es_cero_medido_cuando_el_sistema_no_acerto_nada(tmp_path):
    """2 clips, 4 episodios evaluables, 0 aciertos y 2 FP.

    recall_micro = 0/4 = 0,0 (MEDIDO) y precision_micro = 0/(0+2) = 0,0 (MEDIDO).
    El F1 de dos ceros medidos es 0,0. Devolver None diria "no evaluable" sobre una
    campana que se evaluo entera y fallo entera — el error simetrico al de inventar
    un 0 donde no hay medicion.
    """
    m = _run(tmp_path, [_clip("p1", conditions=("CR-01",) * 2, expected=2, matched=0, fp=1),
                        _clip("p2", conditions=("CR-01",) * 2, expected=2, matched=0, fp=1)])
    p = m["positives"]

    assert p["episodes_evaluable"] == 4
    assert p["recall_micro"] == 0.0
    assert p["precision_micro"] == 0.0
    assert p["f1_micro"] == 0.0


def test_f1_micro_es_none_si_no_hay_episodios_evaluables(tmp_path):
    """Caso REAL del piloto (doc 102): todos los episodios censurados por el gate A1.

    recall no es medible -> F1 tampoco, aunque precision si lo sea (hay FP). Un 0.0
    aca seria un fracaso FABRICADO sobre material que nunca fue juzgable.
    """
    m = _run(tmp_path, [_clip("piloto", conditions=("CR-01",) * 2, expected=2,
                              censored=2, matched=0, fp=3)])
    p = m["positives"]

    assert p["episodes_evaluable"] == 0
    assert p["recall_micro"] is None
    assert p["precision_micro"] == 0.0          # 0/(0+3): medido
    assert p["f1_micro"] is None


@pytest.mark.parametrize("matched,fp,evaluable", [
    (0, 0, 2), (0, 2, 2), (1, 1, 2), (2, 0, 2), (3, 1, 4), (2, 2, 4),
])
def test_f1_micro_usa_la_misma_convencion_que_prf1(tmp_path, matched, fp, evaluable):
    """El repo tiene DOS implementaciones de F1 (esta y `score_person_state.prf1`,
    la de Nivel A). Con episodios evaluables, las dos tienen que dar lo mismo: si
    divergen, el informe reporta dos F1 distintos para la misma situacion."""
    m = _run(tmp_path, [_clip("p", conditions=("CR-01",) * evaluable,
                              expected=evaluable, matched=matched, fp=fp)])
    p = m["positives"]
    esperado = prf1({"tp": matched, "fp": fp, "fn": evaluable - matched})

    assert p["recall_micro"] == pytest.approx(esperado["recall"])
    assert p["precision_micro"] == (None if esperado["precision"] is None
                                    else pytest.approx(esperado["precision"]))
    assert p["f1_micro"] == (None if esperado["f1"] is None
                             else pytest.approx(esperado["f1"], abs=1e-6))


# ---------------------------------------------------------------------------
# Supervivencia: toda media declara su n
# ---------------------------------------------------------------------------

def test_las_medias_declaran_sobre_cuantos_clips_se_calcularon(tmp_path):
    """`t_alert`/`ttfd`/`sdr` se promedian SOLO sobre los clips que alertaron.

    Caso real: la campana `d1_gdinotiny560_edirpair_scene` reporta t_alert = 6611 ms
    promediando 6 de sus 30 clips positivos (24 no alertaron), y `g1` reporta 5236 ms
    sobre 29 de 30. Compararlas de frente es la trampa de supervivencia (F-96): el
    peor detector parece tener latencia comparable porque solo promedia sus casos
    faciles. El JSON tiene que declarar el n de cada media para que se vea.
    """
    m = _run(tmp_path, [
        _clip("acierta", matched=1, t_alert=3000.0, ttfd=100.0, sdr=0.9),
        _clip("falla_1", matched=0, t_alert=None, ttfd=None, sdr=None),
        _clip("falla_2", matched=0, t_alert=None, ttfd=None, sdr=None),
        _clip("falla_3", matched=0, t_alert=None, ttfd=None, sdr=None),
    ])
    p = m["positives"]

    assert p["clips"] == 4
    assert p["t_alert_system_ms"] == 3000.0
    assert p["t_alert_system_ms_n"] == 1        # 1 de 4, y el JSON lo dice
    assert p["ttfd_ms_n"] == 1
    assert p["sdr_n"] == 1
    assert p["recall_macro_n"] == 4             # recall si es computable en los 4


# ---------------------------------------------------------------------------
# Invariantes property-style sobre TODAS las composiciones
# ---------------------------------------------------------------------------

COMPOSICIONES = {
    "un_positivo": [_clip("a", matched=1)],
    "un_negativo_corto": [_neg("a", duration=18_000.0, fp=2)],
    "un_soak": [_neg("a", duration=360_000.0, fp=3)],
    "todos_negativos": [_neg("a", duration=30_000.0, fp=1),
                        _neg("b", duration=360_000.0, fp=2)],
    "todos_positivos": [_clip("a", matched=1), _clip("b", matched=0, fp=2)],
    "sin_soak": [_clip("a", matched=1),
                 _neg("b", duration=60_000.0, fp=1),
                 _neg("c", duration=60_000.0, fp=2)],
    "dos_soak_y_cortos": [
        _clip("a", scenario="P1", matched=1, fp=1),
        _neg("s1", duration=360_000.0, fp=2), _neg("s2", duration=600_000.0, fp=4),
        _neg("c1", duration=30_000.0, fp=5), _neg("c2", duration=30_000.0, fp=5),
    ],
    "duraciones_heterogeneas": [_neg("micro", duration=6_000.0, fp=1),
                                _neg("soak", duration=360_000.0, fp=1)],
    "censurados_mezclados": [
        _clip("A", conditions=("CR-01",) * 3, expected=3, censored=2, matched=1),
        _clip("B", conditions=("CR-01",) * 2, expected=2, matched=1),
        _clip("C", conditions=("CR-01",) * 2, expected=2, censored=2, matched=0),
    ],
    "todo_censurado": [_clip("A", conditions=("CR-01",) * 2, expected=2,
                             censored=2, matched=0, fp=3)],
    "nada_acertado": [_clip("a", conditions=("CR-01",) * 2, expected=2, matched=0, fp=1),
                      _clip("b", conditions=("CR-01",) * 2, expected=2, matched=0, fp=1)],
    "multiescenario_multicondicion": [
        _clip("m1", scenario="P6", conditions=("CR-01", "CR-02"), expected=2,
              matched=1, fp=2),
        _clip("m2", scenario="P7", conditions=("CR-02",), matched=0, fp=1,
              t_alert=None, ttfd=None, sdr=None),
        _neg("m3", scenario="P3", duration=420_000.0, fp=3),
    ],
    "re_alerts": [_clip("a", matched=1, re_alerts=50),
                  _neg("s", duration=360_000.0, re_alerts=20)],
}


@pytest.fixture(params=sorted(COMPOSICIONES))
def composicion(request, tmp_path):
    return request.param, _run(tmp_path, COMPOSICIONES[request.param])


def _reconstruye(tasa, denominador, numerador, contexto):
    """tasa x denominador declarado == numerador crudo.

    Tolerancia proporcional al denominador: `_safe` redondea la tasa a 6 decimales,
    asi que el error de reconstruccion crece con el denominador (recall 1/3 vuelve
    como 0,999999 sobre 3 episodios). Lo que se verifica es la BASE, no el redondeo.
    """
    if tasa is None:
        return
    tol = 1e-6 * max(1.0, abs(denominador))
    assert tasa * denominador == pytest.approx(numerador, abs=tol), contexto


def test_invariante_a_toda_tasa_reconstruye_su_numerador(composicion):
    """(a) numerador y denominador de CADA tasa salen del MISMO subconjunto.

    Es el invariante que el bug de `far_per_hour` violaba. Se comprueba
    reconstruyendo el numerador desde la tasa y su denominador declarado: si la
    tasa se calculo con otra base, la reconstruccion no da el conteo crudo.
    """
    nombre, m = composicion
    p, n = m["positives"], m["negatives"]

    _reconstruye(n["far_per_hour"], n["soak_ms"] / HORA_MS, n["soak_false_positives"],
                 f"{nombre}: FAR declarada mal compuesta")
    _reconstruye(n["far_per_hour_all_negatives"], n["observed_ms"] / HORA_MS,
                 n["false_positives"], f"{nombre}: FAR informativa mal compuesta")
    _reconstruye(p["recall_micro"], p["episodes_evaluable"], p["matched"],
                 f"{nombre}: recall mal compuesto")
    _reconstruye(p["precision_micro"], p["matched"] + p["false_positives"], p["matched"],
                 f"{nombre}: precision mal compuesta")
    # y toda media declara sobre cuantas unidades se calculo
    for clave, n_clave in (("recall_macro", "recall_macro_n"),
                           ("t_alert_system_ms", "t_alert_system_ms_n"),
                           ("ttfd_ms", "ttfd_ms_n"), ("sdr", "sdr_n")):
        assert (p[clave] is None) == (p[n_clave] == 0), f"{nombre}: {clave} sin n coherente"
        assert p[n_clave] <= p["clips"], f"{nombre}: {n_clave} > clips positivos"
    # la misma regla en los desgloses: ninguna media sin su n
    for cond, c in m["by_condition"].items():
        assert (c["sdr"] is None) == (c["sdr_n"] == 0), f"{nombre}/{cond}"
        assert (c["t_alert_system_ms"] is None) == (c["t_alert_system_ms_n"] == 0)
        assert c["sdr_n"] <= c["clips"] and c["t_alert_system_ms_n"] <= c["clips"]
    for esc, s in m["by_scenario"].items():
        assert (s["sdr"] is None) == (s["sdr_n"] == 0), f"{nombre}/{esc}"
        assert s["sdr_n"] <= s["positive_clips"]
        _reconstruye(s["recall"], s["episodes_evaluable"], s["matched"],
                     f"{nombre}/{esc}: recall por escenario mal compuesto")


def test_invariante_b_los_conteos_por_clip_suman_al_agregado(composicion):
    """(b) el desglose por clip y por escenario reconstruye el agregado."""
    nombre, m = composicion
    p, n = m["positives"], m["negatives"]
    pos = [c for c in m["by_clip"] if c["expected"] > 0]
    neg = [c for c in m["by_clip"] if c["expected"] == 0]

    assert len(m["by_clip"]) == m["clips_total"]
    assert len(pos) == p["clips"] and len(neg) == n["clips"]
    assert sum(c["expected"] for c in pos) == p["episodes_total"]
    assert sum(c["censored"] for c in pos) == p["episodes_censored"]
    assert sum(c["matched"] for c in pos) == p["matched"]
    assert sum(c["missed"] for c in pos) == p["missed"]
    assert sum(c["false_positives"] for c in pos) == p["false_positives"]
    assert sum(c["false_positives"] for c in neg) == n["false_positives"]
    assert sum(c["re_alerts"] for c in pos) == p["re_alerts"]
    # by_scenario cubre TODOS los clips (positivos y negativos) sin perder ni duplicar
    assert sum(s["clips"] for s in m["by_scenario"].values()) == m["clips_total"]
    assert sum(s["positive_clips"] for s in m["by_scenario"].values()) == p["clips"]
    assert sum(s["episodes_evaluable"] for s in m["by_scenario"].values()) == p["episodes_evaluable"]
    assert sum(s["matched"] for s in m["by_scenario"].values()) == p["matched"]
    assert (sum(s["false_positives"] for s in m["by_scenario"].values())
            == p["false_positives"] + n["false_positives"])


def test_invariante_b2_by_condition_no_pretende_sumar_al_agregado(composicion):
    """(b') `by_condition` NO es una particion: un clip con episodios CR-01 y CR-02
    aporta sus FP a las DOS condiciones (el eval da FP por clip, no por condicion).

    Es real y esta medido: la campana `d1` tiene 35 FP en positivos y
    sum(by_condition FP) = 41 (+17%); `r4` tiene 2 y suma 3 (+50%). El agregador lo
    declara en `notes` para que nadie sume esa columna. Este test fija la regla:
    la suma por condicion es >= el total, nunca menor (no se pierde ningun FP).
    """
    nombre, m = composicion
    total = m["positives"]["false_positives"]
    suma = sum(c["false_positives"] for c in m["by_condition"].values())
    assert suma >= total, f"{nombre}: by_condition perdio FP"
    assert any("by_condition" in nota for nota in m["notes"]), \
        "el doble conteo por condicion tiene que estar declarado en notes"


def test_invariante_c_micrometricas_consistentes_con_los_conteos(composicion):
    """(c) precision = tp/(tp+fp), recall = tp/evaluables, F1 = media armonica."""
    nombre, m = composicion
    p = m["positives"]
    mat, fp, ev = p["matched"], p["false_positives"], p["episodes_evaluable"]

    assert p["episodes_evaluable"] == p["episodes_total"] - p["episodes_censored"]
    assert p["recall_micro"] == (None if ev == 0 else pytest.approx(mat / ev, abs=1e-6))
    assert p["precision_micro"] == (None if mat + fp == 0
                                    else pytest.approx(mat / (mat + fp), abs=1e-6))
    rm, pm = p["recall_micro"], p["precision_micro"]
    if rm is None:
        assert p["f1_micro"] is None, f"{nombre}: F1 sin recall medible"
    elif not rm or not pm:
        assert p["f1_micro"] == 0.0, f"{nombre}: F1 de un cero medido debe ser 0.0"
    else:
        assert p["f1_micro"] == pytest.approx(2 * rm * pm / (rm + pm), abs=1e-6)
    # el recall por clip nunca excede 1 ni baja de 0
    for c in m["by_clip"]:
        assert c["recall"] is None or 0.0 <= c["recall"] <= 1.0


def test_invariante_d_none_donde_no_es_computable_nunca_cero(composicion):
    """(d) `None` si el denominador no existe; y su reciproco, 0.0 si SI se midio."""
    nombre, m = composicion
    p, n = m["positives"], m["negatives"]

    assert (p["recall_micro"] is None) == (p["episodes_evaluable"] == 0), nombre
    assert (p["precision_micro"] is None) == (p["matched"] + p["false_positives"] == 0), nombre
    assert (n["far_per_hour"] is None) == (n["soak_ms"] == 0), nombre
    assert (n["far_per_hour_all_negatives"] is None) == (n["observed_ms"] == 0), nombre
    # con soak observado y cero FP, la tasa es un CERO MEDIDO, no un hueco
    if n["soak_ms"] > 0 and n["soak_false_positives"] == 0:
        assert n["far_per_hour"] == 0.0, f"{nombre}: cero medido reportado como None"
    if p["clips"] == 0:
        for k in ("recall_micro", "precision_micro", "f1_micro", "recall_macro"):
            assert p[k] is None, f"{nombre}: {k} sin clips positivos"


def test_invariante_e_la_base_declarada_de_far_siempre_se_publica(composicion):
    """La cifra sin su base es una cifra sin sentido: `far_basis` va siempre, aunque
    la tasa sea None (es lo que convierte un hueco en una limitacion declarada)."""
    _, m = composicion
    n = m["negatives"]
    assert n["far_basis"] and "soak" in n["far_basis"].lower()
    assert n["far_all_negatives_basis"]
    assert n["soak_ms"] <= n["observed_ms"]
    assert n["soak_false_positives"] <= n["false_positives"]
    assert n["soak_clips"] <= n["clips"]
