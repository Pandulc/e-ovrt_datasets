"""Stress de COMPOSICIÓN EXTREMA del scorer de Nivel A sobre clips (doc 105).

Complementa `test_score_clip_person_state.py`, que cubre la mecánica (geometría,
escalón de atributos, región, stride) sobre una fixture "normal". Acá se estresan
las composiciones DEGENERADAS, que son donde una métrica se rompe sin fallar:

- 0 person-frames (clip sin personas anotadas);
- clip entero en `unknown` (el caso real de los estratos far-field);
- un solo frame;
- GT sin violadores de la condición evaluada (recall indefinido);
- GT truncado por `n_frames` y GT que no cae en la grilla del `stride`.

La pregunta que responden: ¿alguna de estas composiciones divide por cero, inventa
un 0 donde no hay medición, o hace que el MISMO conjunto de detecciones se puntúe
distinto? La última la responde `test_las_predicciones_sobre_unknown_...`, y la
respuesta es que SÍ (ver su docstring).
"""
import json

import pytest

from bench.score_clip_person_state import gt_por_frame, puntuar_clip

# Persona A y persona B, separadas para que ninguna prediccion matchee a las dos.
A = [100, 100, 200, 400]
B = [400, 100, 500, 400]


def _attrs(**kw):
    return "".join(f'<attribute name="{k}">{"true" if v else "false"}</attribute>'
                   for k, v in kw.items() if v is not None)


def _track(tid, bbox, frames, *, label="person", cierre=None, **atributos):
    """Track CVAT con UNA CAJA POR FRAME (como emite el export real 'for video 1.1').

    Los atributos mutables se repiten en cada caja, tambien en las interpoladas:
    verificado contra los XML del banco. Un atributo omitido = `unknown`.
    """
    filas = [
        f'<box frame="{f}" keyframe="{1 if f == frames[0] else 0}" outside="0" '
        f'occluded="0" xtl="{bbox[0]}" ytl="{bbox[1]}" xbr="{bbox[2]}" '
        f'ybr="{bbox[3]}">{_attrs(**atributos)}</box>' for f in frames
    ]
    if cierre is not None:
        filas.append(
            f'<box frame="{cierre}" keyframe="1" outside="1" occluded="0" '
            f'xtl="{bbox[0]}" ytl="{bbox[1]}" xbr="{bbox[2]}" ybr="{bbox[3]}"></box>')
    return f'<track id="{tid}" label="{label}">' + "".join(filas) + "</track>"


def _xml(tmp_path, tracks, size, nombre="clip.xml"):
    p = tmp_path / nombre
    p.write_text(
        '<annotations><version>1.1</version><meta><task><id>1</id>'
        f'<name>{nombre}</name><size>{size}</size><start_frame>0</start_frame>'
        f'<stop_frame>{size - 1}</stop_frame></task></meta>'
        + "".join(tracks) + '</annotations>')
    return p


def _det(label, bbox, conf=0.9):
    return {"label": label, "confidence": conf, "bbox_xyxy": bbox}


def _run_dir(tmp_path, eventos, nombre="run"):
    d = tmp_path / nombre
    d.mkdir(exist_ok=True)
    (d / "detections.jsonl").write_text("\n".join(
        json.dumps({"schema_version": "media.detection.v1",
                    "source": {"source_id": "clip", "frame_index": f},
                    "detections": dets}) for f, dets in eventos) + "\n")
    return d


def _ve_personas(frames, personas):
    """El sistema detecta a esas personas (y ninguna evidencia de EPP) en cada frame."""
    return [(f, [_det("person", b) for b in personas]) for f in frames]


# ---------------------------------------------------------------------------
# Composiciones degeneradas
# ---------------------------------------------------------------------------

def test_cero_person_frames_no_divide_por_cero(tmp_path):
    """Clip sin ninguna persona anotada: todo indefinido, nada en 0.

    `ratio_unknown` en particular tiene que ser None y no 0.0: "0% de unknown" es
    una afirmacion sobre un GT que no existe.
    """
    xml = _xml(tmp_path, [_track(0, [10, 10, 50, 50], [0, 1], label="helmet")], size=2)
    run = _run_dir(tmp_path, _ve_personas([0, 1], [A]))
    r = puntuar_clip("clip", xml, run, 2, stride=1)

    assert r["frames_puntuados"] == 0
    for cond in ("CR-01", "CR-02"):
        d = r["por_condicion"][cond]
        assert d["tp"] == d["fp"] == d["fn"] == 0
        assert d["n_gt"] == 0 and d["n_gt_positive"] == 0
        assert d["precision"] is None and d["recall"] is None and d["f1"] is None
        assert d["person_frames_evaluadas"] == 0
        assert d["person_frames_excluidas_unknown"] == 0
        assert d["ratio_unknown"] is None, "0/0 no es 0%"


def test_todos_los_atributos_unknown_excluye_todo_sin_dividir_por_cero(tmp_path):
    """2 personas x 3 frames, ningun atributo declarado: 6 person-frames excluidas.

    Es el limite del caso far-field real (doc 105: hasta 55% de unknown). El
    denominador queda vacio y las metricas tienen que quedar en None — un 0.0 aca
    diria que el sistema fallo en todo cuando en realidad no se lo pudo juzgar.
    """
    xml = _xml(tmp_path, [_track(0, A, [0, 1, 2]), _track(1, B, [0, 1, 2])], size=3)
    run = _run_dir(tmp_path, _ve_personas([0, 1, 2], [A, B]))
    r = puntuar_clip("clip", xml, run, 3, stride=1)

    assert r["frames_puntuados"] == 3
    for cond in ("CR-01", "CR-02"):
        d = r["por_condicion"][cond]
        assert d["person_frames_evaluadas"] == 0
        assert d["person_frames_excluidas_unknown"] == 6     # 2 personas x 3 frames
        assert d["ratio_unknown"] == 1.0
        assert d["tp"] == d["fp"] == d["fn"] == 0
        assert d["precision"] is None and d["recall"] is None and d["f1"] is None


def test_una_condicion_evaluable_y_la_otra_toda_unknown(tmp_path):
    """El denominador es POR CONDICION: el chaleco anotado no vuelve evaluable al casco.

    Persona con `has_vest` conocido y `has_helmet` unknown en todo el clip.
    """
    xml = _xml(tmp_path, [_track(0, A, [0, 1], has_vest=True)], size=2)
    run = _run_dir(tmp_path, _ve_personas([0, 1], [A]))
    r = puntuar_clip("clip", xml, run, 2, stride=1)

    cr01, cr02 = r["por_condicion"]["CR-01"], r["por_condicion"]["CR-02"]
    assert cr01["person_frames_evaluadas"] == 0 and cr01["ratio_unknown"] == 1.0
    assert cr01["precision"] is None and cr01["recall"] is None
    assert cr02["person_frames_evaluadas"] == 2 and cr02["ratio_unknown"] == 0.0
    assert cr02["n_gt"] == 2 and cr02["n_gt_positive"] == 0
    assert cr02["fp"] == 2                       # cumplidora marcada 2 veces


def test_un_solo_frame(tmp_path):
    """1 frame, 1 persona sin casco y con chaleco. A mano:
      CR-01: 1 violadora, el sistema no ve casco -> tp=1, P=R=F1=1,0
      CR-02: 0 violadoras, el sistema no ve chaleco -> fp=1, P=0,0 y R indefinido
    """
    xml = _xml(tmp_path, [_track(0, A, [0], has_helmet=False, has_vest=True)], size=1)
    run = _run_dir(tmp_path, _ve_personas([0], [A]))
    r = puntuar_clip("clip", xml, run, 1, stride=15)   # stride > n_frames: solo el 0

    assert r["frames_puntuados"] == 1
    cr01 = r["por_condicion"]["CR-01"]
    assert (cr01["tp"], cr01["fp"], cr01["fn"]) == (1, 0, 0)
    assert cr01["precision"] == 1.0 and cr01["recall"] == 1.0 and cr01["f1"] == 1.0
    assert cr01["person_frames_evaluadas"] == 1 and cr01["ratio_unknown"] == 0.0
    cr02 = r["por_condicion"]["CR-02"]
    assert (cr02["tp"], cr02["fp"], cr02["fn"]) == (0, 1, 0)
    assert cr02["precision"] == 0.0 and cr02["recall"] is None


def test_gt_sin_violadores_de_la_condicion_deja_recall_indefinido(tmp_path):
    """2 personas CON casco: CR-01 no tiene violadores que encontrar.

    n_gt=2, n_gt_positive=0, fn=0, fp=2 -> precision 0,0 MEDIDA, recall INDEFINIDO.
    El F1 sale 0,0 por la convencion de `prf1` (la misma de sklearn con
    zero_division=0), y ESE es el origen de las filas `R = — / F1 = 0,000` de la
    tabla del doc 105 (`video02_clip07` CR-01, `video15_clip01` CR-01,
    `video16_clip14` CR-01, las tres con 0 violadores). El 0,000 no es una medicion
    de F1: es una convencion sobre un recall que no existe. Este test la FIJA para
    que sea explicita, no accidental — la fila hay que leerla por su precision.
    """
    xml = _xml(tmp_path, [_track(0, A, [0], has_helmet=True),
                          _track(1, B, [0], has_helmet=True)], size=1)
    run = _run_dir(tmp_path, _ve_personas([0], [A, B]))
    cr01 = puntuar_clip("clip", xml, run, 1, stride=1)["por_condicion"]["CR-01"]

    assert cr01["n_gt"] == 2 and cr01["n_gt_positive"] == 0
    assert (cr01["tp"], cr01["fp"], cr01["fn"]) == (0, 2, 0)
    assert cr01["precision"] == 0.0
    assert cr01["recall"] is None
    assert cr01["f1"] == 0.0, "convencion prf1/sklearn: NO es una medicion de F1"


def test_las_predicciones_sobre_unknown_solo_cuestan_FP_si_hay_alguien_conocido(tmp_path):
    """ASIMETRIA MEDIDA: el mismo conjunto de detecciones se puntua distinto segun
    lo que un anotador escribio sobre OTRA persona del mismo frame.

    Las dos escenas tienen 2 personas y detecciones IDENTICAS (el sistema marca a
    las dos como en violacion). Lo unico que cambia es el GT de la persona A:

      escena "ambas unknown": `conocidas` queda vacia -> el frame se saltea entero
                              -> fp = 0. La prediccion sobre B sale gratis.
      escena "A conocida"   : el frame se puntua -> A es tp, y la prediccion sobre
                              B (que sigue siendo unknown) cuenta fp = 1.

    Es decir: la prediccion sobre la persona `unknown` cuesta 0 o 1 FP segun la
    composicion del frame. La decision 1 del scorer dice que `unknown` se EXCLUYE
    (ni cumplimiento ni violacion), pero la exclusion es completa solo a nivel
    FRAME y parcial a nivel PERSONA. Consecuencia para el informe: en clips con
    mucho unknown la precision de Nivel A depende de como se REPARTAN los unknown
    entre frames, no solo de cuantos haya. Queda fijado aca para que sea una
    decision visible y no una propiedad emergente.

    ESTADO MEDIDO: en los 4 clips piloto del doc 105 (17,4% y 20,6% de unknown) NO
    hay un solo frame con TODAS las personas unknown, asi que el salteo nunca se
    dispara y el conteo es identico con y sin el (190/346 FP en ambos casos). La
    inconsistencia esta LATENTE: la composicion actual no la estresa. Se disparara
    en material far-field, donde frames enteros salen unknown — que es exactamente
    el estrato B pendiente de correr.
    """
    xml_ambas = _xml(tmp_path, [_track(0, A, [0]), _track(1, B, [0])],
                     size=1, nombre="ambas.xml")
    xml_una = _xml(tmp_path, [_track(0, A, [0], has_helmet=False), _track(1, B, [0])],
                   size=1, nombre="una.xml")
    run = _run_dir(tmp_path, _ve_personas([0], [A, B]))

    ambas = puntuar_clip("c", xml_ambas, run, 1, stride=1)["por_condicion"]["CR-01"]
    una = puntuar_clip("c", xml_una, run, 1, stride=1)["por_condicion"]["CR-01"]

    assert ambas["n_gt"] == 0 and ambas["fp"] == 0
    assert ambas["person_frames_excluidas_unknown"] == 2
    assert una["n_gt"] == 1 and una["tp"] == 1
    assert una["fp"] == 1, "la prediccion sobre la persona unknown ahora SI es FP"
    assert una["person_frames_excluidas_unknown"] == 1
    # misma deteccion sobre la misma persona unknown: 0 FP en un caso, 1 en el otro
    assert una["fp"] - ambas["fp"] == 1


def test_una_prediccion_sobre_persona_unknown_cuenta_FP_aunque_ella_no_este_en_n_gt(tmp_path):
    """La persona `unknown` sale del DENOMINADOR pero su prediccion entra al NUMERADOR.

    A (unknown, fuera de n_gt) y B (violadora, dentro): el sistema marca a las dos.
    Resultado: n_gt = 1 y fp = 1 — la precision 1/2 se calcula sobre un conjunto de
    personas que no es el que declara `n_gt`. Es la misma forma del bug de
    `far_per_hour`: numerador y denominador de subconjuntos distintos.

    MEDIDO sobre los 4 clips piloto del doc 105 (mismas detecciones, misma GT, unica
    diferencia la regla): descartar las predicciones que caen sobre personas
    `unknown` saca **91 de los 190 FP de CR-01 (48%)** y **77 de los 346 de CR-02
    (22%)**; la precision pasaria de 0,0052 a 0,0100 en CR-01 y de 0,1013 a 0,1266
    en CR-02, con recall intacto (0,333 / 0,325).

    NO se cambia el comportamiento: hay una lectura operativa legitima del actual
    ("la alerta sobre una persona que el anotador no pudo juzgar igual suena, y
    molesta al operario"), y es una adjudicacion que mueve numeros ya publicados
    (doc 105 y `results/bench_nivel_a/na1_...`). Este test la vuelve una decision
    EXPLICITA y tasada: si alguien la cambia, falla acá y con el numero al lado.
    """
    xml = _xml(tmp_path, [_track(0, A, [0]),                              # unknown
                          _track(1, B, [0], has_helmet=False)], size=1)   # violadora
    run = _run_dir(tmp_path, _ve_personas([0], [A, B]))
    cr01 = puntuar_clip("c", xml, run, 1, stride=1)["por_condicion"]["CR-01"]

    assert cr01["n_gt"] == 1 and cr01["n_gt_positive"] == 1
    assert cr01["person_frames_evaluadas"] == 1
    assert cr01["person_frames_excluidas_unknown"] == 1
    assert (cr01["tp"], cr01["fp"], cr01["fn"]) == (1, 1, 0)
    assert cr01["precision"] == 0.5      # 1/(1+1): el denominador NO es n_gt
    assert cr01["recall"] == 1.0


def test_el_gt_se_trunca_en_silencio_si_n_frames_es_menor_que_el_xml(tmp_path):
    """`gt_por_frame` descarta los frames >= n_frames sin avisar.

    A diferencia de `derive_clip_gt` (guard I2: size del XML vs n_frames del clip),
    este scorer no compara. Si el `info.json` trae menos frames que el XML, el
    denominador se achica en silencio. Se fija el comportamiento para que la
    proteccion sea el `frames_puntuados` del reporte, que si es auditable.
    """
    xml = _xml(tmp_path, [_track(0, A, [0, 1, 2, 3, 4, 5], has_helmet=False)], size=6)
    assert len(gt_por_frame(xml, 6)) == 6
    assert len(gt_por_frame(xml, 2)) == 2

    run = _run_dir(tmp_path, _ve_personas(range(6), [A]))
    completo = puntuar_clip("c", xml, run, 6, stride=1)
    truncado = puntuar_clip("c", xml, run, 2, stride=1)
    assert completo["frames_puntuados"] == 6 and truncado["frames_puntuados"] == 2
    assert completo["por_condicion"]["CR-01"]["tp"] == 6
    assert truncado["por_condicion"]["CR-01"]["tp"] == 2


def test_gt_fuera_de_la_grilla_del_stride_no_puntua_nada_pero_lo_declara(tmp_path):
    """El sub-muestreo es `f % stride == 0`: un GT que empieza en el frame 1 y un
    stride de 15 no comparten ningun frame y el clip se puntua sobre CERO.

    No hay excepcion ni cero fabricado — las metricas quedan en None y
    `frames_puntuados` en 0, que es el campo que hay que mirar antes de agregar.
    """
    xml = _xml(tmp_path, [_track(0, A, [1, 2, 3], has_helmet=False)], size=4)
    run = _run_dir(tmp_path, _ve_personas([1, 2, 3], [A]))
    r = puntuar_clip("c", xml, run, 4, stride=15)

    assert r["frames_puntuados"] == 0
    cr01 = r["por_condicion"]["CR-01"]
    assert cr01["n_gt"] == 0 and cr01["tp"] == 0
    assert cr01["precision"] is None and cr01["recall"] is None
    assert cr01["ratio_unknown"] is None


@pytest.mark.parametrize("stride", [1, 2, 3, 5])
def test_invariante_las_person_frames_cierran_con_el_denominador(tmp_path, stride):
    """Invariante: evaluadas + excluidas == person-frames de los frames puntuados, y
    n_gt (denominador del matching) == evaluadas. Si divergen, el scorer esta
    contando personas en una metrica y frames en otra."""
    xml = _xml(tmp_path, [
        _track(0, A, list(range(6)), has_helmet=False, has_vest=True),   # conocida
        _track(1, B, list(range(6)), has_vest=True),                     # helmet unknown
    ], size=6)
    run = _run_dir(tmp_path, _ve_personas(range(6), [A, B]))
    r = puntuar_clip("c", xml, run, 6, stride=stride)
    puntuados = r["frames_puntuados"]

    cr01 = r["por_condicion"]["CR-01"]
    assert cr01["person_frames_evaluadas"] + cr01["person_frames_excluidas_unknown"] \
        == 2 * puntuados
    assert cr01["n_gt"] == cr01["person_frames_evaluadas"]
    assert cr01["ratio_unknown"] == pytest.approx(0.5)
    cr02 = r["por_condicion"]["CR-02"]
    assert cr02["person_frames_evaluadas"] == 2 * puntuados
    assert cr02["person_frames_excluidas_unknown"] == 0
    assert cr02["n_gt"] == cr02["person_frames_evaluadas"]
    # tp + fn nunca supera a los violadores del GT, ni n_gt a las evaluadas
    for d in (cr01, cr02):
        assert d["tp"] + d["fn"] == d["n_gt_positive"]
        assert d["n_gt_positive"] <= d["n_gt"]
