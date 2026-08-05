"""Fusion dual-run de corridas para E-HYB a Nivel B (doc 12 §4.1).

El pre-registro prohibe el pase unico de vocabulario union: en GDINO el vocabulario
es parte de la inferencia, asi que un caption con las 5 clases produciria señales
DISTINTAS de las de T1 y D1 y la comparacion dejaria de ser de variable unica. La
fusion se hace sobre las corridas YA EXISTENTES — por eso E-HYB a Nivel B no
necesita GPU.

Que el problema es real esta medido: las detecciones de `person` de T1 y D1 diferen
(729 vs 731 en a_p1_c09, 1095 vs 1317 en a_p2_c01) con la MISMA frase "person",
solo porque el resto del caption cambia.

Regla de la fusion, que estos tests fijan:
  - Del stream E-IND entra TODO (person/helmet/vest) -> `spatial_absence` ve
    exactamente lo que vio en T1 y su evidencia es bit a bit la misma.
  - Del stream E-DIR entran SOLO las clases de evidencia directa; sus `person` se
    descartan para no duplicar sujetos (dos cajas por persona romperian el conteo
    de `subjects_in_evidence` y la evidencia de T1).
  - La identidad del frame (frame_index, timestamp) manda: los streams se unen por
    frame, y un frame que no este en ambos es un error, no un silencio.
"""
import json

import pytest

from bench.merge_dual_run import merge_detection_streams, merge_event


def _ev(frame, dets, *, ts=None, run="run-x", source_id="clip.mp4"):
    return {
        "schema_version": "media.detection.v1",
        "event_type": "detection_event",
        "run_id": run,
        "unit_id": f"unit_{frame:06d}",
        "source": {"source_id": source_id, "source_type": "video", "width": 640,
                   "height": 480, "frame_index": frame,
                   "timestamp_ms": ts if ts is not None else frame * 33.3},
        "model": {"name": "grounding_dino"},
        "prompts": {"prompt_set_id": "x"},
        "detections": dets,
    }


def _det(label, conf=0.8, bbox=None, det_id="det_000001"):
    return {"detection_id": det_id, "label": label, "prompt_id": label,
            "confidence": conf, "bbox_xyxy": bbox or [10, 10, 50, 100]}


DIRECT = ("cr01_spec", "cr02_obs")


# ---------------------------------------------------------------------------
# Fusion de un evento
# ---------------------------------------------------------------------------

def test_conserva_todas_las_detecciones_del_stream_eind():
    a = _ev(0, [_det("person"), _det("helmet"), _det("vest")])
    b = _ev(0, [_det("person"), _det("cr01_spec")])
    out = merge_event(a, b, DIRECT)
    labels = [d["label"] for d in out["detections"]]
    assert labels.count("person") == 1        # solo la de E-IND
    assert "helmet" in labels and "vest" in labels


def test_incorpora_la_evidencia_directa_del_stream_edir():
    a = _ev(0, [_det("person")])
    b = _ev(0, [_det("person"), _det("cr01_spec", conf=0.42)])
    out = merge_event(a, b, DIRECT)
    directas = [d for d in out["detections"] if d["label"] == "cr01_spec"]
    assert len(directas) == 1
    assert directas[0]["confidence"] == 0.42   # bit a bit la de D1


def test_descarta_las_personas_del_stream_edir():
    """Dos cajas por persona romperian subjects_in_evidence y la evidencia de T1."""
    a = _ev(0, [_det("person", bbox=[0, 0, 100, 200])])
    b = _ev(0, [_det("person", bbox=[3, 3, 103, 203]), _det("cr01_spec")])
    out = merge_event(a, b, DIRECT)
    personas = [d for d in out["detections"] if d["label"] == "person"]
    assert len(personas) == 1
    assert personas[0]["bbox_xyxy"] == [0, 0, 100, 200]   # la de E-IND


def test_ignora_clases_del_stream_edir_que_no_son_de_evidencia_directa():
    a = _ev(0, [_det("person")])
    b = _ev(0, [_det("person"), _det("otra_cosa"), _det("cr01_spec")])
    out = merge_event(a, b, DIRECT)
    assert {d["label"] for d in out["detections"]} == {"person", "cr01_spec"}


def test_los_detection_id_del_stream_edir_no_colisionan():
    """Ambas corridas numeran det_000001...: sin namespace se pisan en los sinks."""
    a = _ev(0, [_det("person", det_id="det_000001")])
    b = _ev(0, [_det("cr01_spec", det_id="det_000001")])
    out = merge_event(a, b, DIRECT)
    ids = [d["detection_id"] for d in out["detections"]]
    assert len(set(ids)) == 2


def test_conserva_la_identidad_del_frame_del_stream_eind():
    a = _ev(7, [_det("person")], ts=233.1, run="run-eind")
    b = _ev(7, [_det("cr01_spec")], ts=233.1, run="run-edir")
    out = merge_event(a, b, DIRECT)
    assert out["source"]["frame_index"] == 7
    assert out["source"]["timestamp_ms"] == 233.1
    assert out["unit_id"] == a["unit_id"]


def test_declara_la_procedencia_de_los_dos_streams():
    """Sin esto, dentro de seis meses nadie sabe de qué corridas salió la fusión."""
    a = _ev(0, [_det("person")], run="run-eind")
    b = _ev(0, [_det("cr01_spec")], run="run-edir")
    out = merge_event(a, b, DIRECT)
    assert out["prompts"]["prompt_set_id"] == "hyb_or_dual_run"
    assert out["fusion"] == {"eind_run_id": "run-eind", "edir_run_id": "run-edir"}


# ---------------------------------------------------------------------------
# Fusion de streams completos
# ---------------------------------------------------------------------------

def test_fusiona_frame_a_frame(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text("\n".join(json.dumps(_ev(i, [_det("person")])) for i in range(3)))
    b.write_text("\n".join(json.dumps(_ev(i, [_det("cr01_spec")])) for i in range(3)))
    out = tmp_path / "out.jsonl"
    stats = merge_detection_streams(a, b, out, DIRECT)
    lineas = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
    assert len(lineas) == 3
    assert stats["frames"] == 3
    assert stats["direct_hits"] == 3


def test_un_frame_que_falta_en_un_stream_es_error(tmp_path):
    """Alinear a ciegas cruzaría evidencia de frames distintos EN SILENCIO — la
    misma familia de trampa que el mtime del doc 82 y el export de CVAT."""
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text("\n".join(json.dumps(_ev(i, [_det("person")])) for i in range(3)))
    b.write_text("\n".join(json.dumps(_ev(i, [_det("cr01_spec")])) for i in (0, 2)))
    with pytest.raises(ValueError, match="frame"):
        merge_detection_streams(a, b, tmp_path / "out.jsonl", DIRECT)


def test_timestamps_discordantes_son_error(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text(json.dumps(_ev(0, [_det("person")], ts=100.0)))
    b.write_text(json.dumps(_ev(0, [_det("cr01_spec")], ts=999.0)))
    with pytest.raises(ValueError, match="timestamp"):
        merge_detection_streams(a, b, tmp_path / "out.jsonl", DIRECT)


def test_source_id_discordante_es_error(tmp_path):
    """Fusionar dos clips distintos es exactamente el cruce que hay que impedir."""
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text(json.dumps(_ev(0, [_det("person")], source_id="a_p1_c02.mp4")))
    b.write_text(json.dumps(_ev(0, [_det("cr01_spec")], source_id="a_p7_c01.mp4")))
    with pytest.raises(ValueError, match="source_id"):
        merge_detection_streams(a, b, tmp_path / "out.jsonl", DIRECT)
