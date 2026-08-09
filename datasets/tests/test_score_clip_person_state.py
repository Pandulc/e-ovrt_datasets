"""Tests del scoring de Nivel A sobre clips de video (fixture sintética, doc 105).

Los riesgos que cubren, en orden de gravedad:

1. **`unknown` contado como cumplimiento o como violación.** La decisión central del
   scorer es EXCLUIR del denominador las person-frames cuyo atributo es `unknown`
   (mismo principio que `derive_clip_gt`: la incertidumbre nunca fabrica una
   violación — y tampoco debe fabricar un FP contra el sistema). Si una regresión
   las cuenta como `True`, un violador real marcado unknown se vuelve FP del
   sistema; si las cuenta como `False`, el GT fabrica violadores.
2. **Geometría del XML.** `videogt.cvat_xml` no expone cajas (a `derive_clip_gt` no
   le hacen falta); el scorer las lee aparte. Una caja `outside=1` que entra al GT
   inflaría el denominador con personas que no están en cuadro.
3. **Semántica escalón de los atributos.** El atributo vale hasta el próximo
   keyframe que lo cambie; si el scorer leyera solo el keyframe exacto, los frames
   intermedios saldrían unknown y el denominador se vaciaría en silencio.
4. **La región importa.** Un chaleco detectado FUERA del torso de la persona no debe
   suprimir la predicción de violación (misma aritmética que `spatial_absence`).
5. **El sub-muestreo (`stride`) puntúa solo los frames que dice puntuar.**
"""
import json
import textwrap

import pytest

from bench.score_clip_person_state import (
    detecciones_por_frame,
    gt_por_frame,
    puntuar_clip,
)

# Clip sintético de 6 frames, 2 personas. FIEL AL EXPORT REAL: "CVAT for video
# 1.1" emite UNA CAJA POR FRAME (las interpoladas con keyframe="0"), no solo los
# keyframes — el scorer itera los frames que traen GT, así que el fixture debe
# traerlos todos.
#  - track 0 ("violador"): sin casco (has_helmet=false) todo el clip; chaleco true.
#    Visible frames 0–4, cierra con outside=1 en el 5.
#  - track 1 ("incierto"): has_helmet unknown TODO el clip (sin atributo en el
#    keyframe); has_vest true. Visible frames 0–3, cierra outside=1 en el 4.
def _boxes(frames_visibles, frame_cierre, bbox, attrs):
    # El export real repite los atributos mutables EN CADA caja (también en las
    # interpoladas, keyframe="0") — verificado contra los XML del banco. Un
    # fixture que los ponga solo en el keyframe produce None en los frames
    # intermedios (attribute_states lee la caja vigente, no "el último keyframe
    # con atributo") y no representa lo que CVAT emite.
    filas = []
    for f in frames_visibles:
        filas.append(
            f'<box frame="{f}" keyframe="{1 if f == 0 else 0}" outside="0" '
            f'occluded="0" xtl="{bbox[0]}" ytl="{bbox[1]}" xbr="{bbox[2]}" '
            f'ybr="{bbox[3]}">{attrs}</box>')
    filas.append(
        f'<box frame="{frame_cierre}" keyframe="1" outside="1" occluded="0" '
        f'xtl="{bbox[0]}" ytl="{bbox[1]}" xbr="{bbox[2]}" ybr="{bbox[3]}"></box>')
    return "\n".join(filas)


CLIP_XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta>
        <task>
          <id>1</id><name>clip_t</name><size>6</size>
          <start_frame>0</start_frame><stop_frame>5</stop_frame>
        </task>
      </meta>
      <track id="0" label="person">
    {t0}
      </track>
      <track id="1" label="person">
    {t1}
      </track>
    </annotations>
""").format(
    t0=_boxes(range(0, 5), 5, [100, 100, 200, 400],
              '<attribute name="has_helmet">false</attribute>'
              '<attribute name="has_vest">true</attribute>'),
    t1=_boxes(range(0, 4), 4, [400, 100, 500, 400],
              '<attribute name="has_vest">true</attribute>'),
)

N_FRAMES = 6


@pytest.fixture()
def xml_path(tmp_path):
    p = tmp_path / "clip_t.xml"
    p.write_text(CLIP_XML)
    return p


def _evento(frame, detections):
    return {"schema_version": "media.detection.v1",
            "source": {"source_id": "clip_t", "frame_index": frame},
            "detections": detections}


def _det(label, bbox, conf=0.9):
    return {"label": label, "confidence": conf, "bbox_xyxy": bbox}


def _run_dir(tmp_path, eventos):
    d = tmp_path / "run"
    d.mkdir(exist_ok=True)
    (d / "detections.jsonl").write_text(
        "\n".join(json.dumps(e) for e in eventos) + "\n")
    return d


# ---------------------------------------------------------------------------
# GT desde el XML
# ---------------------------------------------------------------------------

def test_gt_geometria_y_escalon(xml_path):
    gt = gt_por_frame(xml_path, N_FRAMES)
    # frame 2: sin keyframe propio — la caja interpolada del export es una por
    # frame; nuestro fixture solo trae keyframes, así que el frame 2 solo tiene
    # lo que el XML trae. El export real emite una caja por frame; acá validamos
    # que las que están se leen con su geometría exacta.
    f0 = gt[0]
    assert len(f0) == 2
    violador = next(r for r in f0 if r["track_id"] == 0)
    assert violador["person_bbox"] == [100.0, 100.0, 200.0, 400.0]
    assert violador["has_helmet"] is False
    # y en un frame intermedio (caja interpolada) el atributo sigue presente
    assert next(r for r in gt[2] if r["track_id"] == 0)["has_helmet"] is False
    incierto = next(r for r in f0 if r["track_id"] == 1)
    # track 1 nunca declaró has_helmet -> unknown (None)
    assert incierto["has_helmet"] is None
    assert incierto["has_vest"] is True


def test_gt_excluye_outside(xml_path):
    gt = gt_por_frame(xml_path, N_FRAMES)
    # track 0 cierra con outside=1 en frame 5; track 1 en frame 4
    assert all(r["track_id"] != 1 for r in gt.get(4, []))
    assert 5 not in gt or all(r["track_id"] not in (0, 1) for r in gt[5])


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def test_violador_detectado_es_tp(xml_path, tmp_path):
    # el sistema ve a la persona violadora y NO ve casco -> predicción correcta
    run = _run_dir(tmp_path, [_evento(0, [_det("person", [105, 105, 195, 395])])])
    r = puntuar_clip("clip_t", xml_path, run, N_FRAMES, stride=N_FRAMES)  # solo frame 0
    cr01 = r["por_condicion"]["CR-01"]
    assert cr01["tp"] == 1 and cr01["fn"] == 0
    # el track incierto quedó EXCLUIDO del denominador de CR-01, no como FP
    assert cr01["person_frames_excluidas_unknown"] == 1
    assert cr01["person_frames_evaluadas"] == 1


def test_unknown_no_es_fp_ni_cumplimiento(xml_path, tmp_path):
    # el sistema también "ve" al incierto sin casco; como su GT es unknown,
    # la persona no está en el denominador y esa predicción no puede ser FP
    # (matching 1:1: la predicción sobre el incierto no matchea a nadie activo,
    # y ahí SÍ cuenta FP por alucinación — validamos el conteo exacto)
    run = _run_dir(tmp_path, [_evento(0, [
        _det("person", [105, 105, 195, 395]),
        _det("person", [405, 105, 495, 395]),
    ])])
    r = puntuar_clip("clip_t", xml_path, run, N_FRAMES, stride=N_FRAMES)
    cr01 = r["por_condicion"]["CR-01"]
    # violador -> TP; predicción sobre el incierto -> FP "sin persona del GT
    # activa" (la persona existe pero está fuera del denominador de CR-01)
    assert cr01["tp"] == 1
    assert cr01["fp"] == 1
    assert cr01["n_gt"] == 1          # solo el violador cuenta
    # CR-02: los dos tracks tienen has_vest=true conocido -> denominador 2,
    # y ambas predicciones de "sin chaleco" son FP (cumplidores marcados)
    cr02 = r["por_condicion"]["CR-02"]
    assert cr02["n_gt"] == 2 and cr02["fp"] == 2 and cr02["tp"] == 0


def test_evidencia_en_region_suprime_prediccion(xml_path, tmp_path):
    # casco DENTRO de la región upper_body del violador -> E-IND no predice
    # violación -> el violador real queda FN
    run = _run_dir(tmp_path, [_evento(0, [
        _det("person", [105, 105, 195, 395]),
        _det("helmet", [130, 110, 170, 150]),          # centro en el tercio superior
    ])])
    r = puntuar_clip("clip_t", xml_path, run, N_FRAMES, stride=N_FRAMES)
    cr01 = r["por_condicion"]["CR-01"]
    assert cr01["tp"] == 0 and cr01["fn"] == 1


def test_evidencia_fuera_de_region_no_suprime(xml_path, tmp_path):
    # casco en el suelo (fuera de la persona): la violación se sigue prediciendo
    run = _run_dir(tmp_path, [_evento(0, [
        _det("person", [105, 105, 195, 395]),
        _det("helmet", [700, 700, 740, 740]),
    ])])
    r = puntuar_clip("clip_t", xml_path, run, N_FRAMES, stride=N_FRAMES)
    assert r["por_condicion"]["CR-01"]["tp"] == 1


def test_stride_puntua_solo_los_frames_que_dice(xml_path, tmp_path):
    # stride=2 sobre 6 frames -> frames 0,2,4; el 4 ya no tiene al track 1
    run = _run_dir(tmp_path, [_evento(f, []) for f in range(N_FRAMES)])
    r = puntuar_clip("clip_t", xml_path, run, N_FRAMES, stride=2)
    # el reporte declara los frames puntuados y el denominador es consistente
    assert r["frames_puntuados"] == 3
    cr02 = r["por_condicion"]["CR-02"]
    # track 0 presente en 0,2,4 (3 frames) + track 1 en 0,2 (2 frames) = 5
    assert cr02["person_frames_evaluadas"] == 5


def test_detecciones_por_frame(tmp_path):
    run = _run_dir(tmp_path, [
        _evento(0, [_det("person", [0, 0, 10, 10])]),
        _evento(3, [_det("vest", [1, 1, 5, 5]), _det("person", [0, 0, 9, 9])]),
    ])
    d = detecciones_por_frame(run)
    assert set(d) == {0, 3} and len(d[3]) == 2
