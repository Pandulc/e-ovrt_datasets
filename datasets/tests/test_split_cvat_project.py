"""Tests del splitter de exports CVAT a nivel PROYECTO (fixture sintético).

El riesgo que cubren: un export de proyecto numera los frames en un espacio
GLOBAL y continuo (task 2 empieza donde termina task 1), mientras que
`parse_cvat_video_xml` + `derive_clip_gt` asumen frames 0-based por clip. Sin
rebase, TODAS las cajas caen fuera de `[0, n_frames-1]`, `attribute_states`
devuelve None en todo el timeline y el GT sale `negative: true` en silencio —
el guard C2 no lo atrapa porque los tracks 'person' SÍ existen.
"""
import textwrap

import pytest

from videogt.cvat_xml import attribute_states, parse_cvat_video_xml
from videogt.split_cvat_project import split_project_export

# task 1: size 4 -> offset 0, frames globales 0..3
# task 2: size 3 -> offset 4, frames globales 4..6
PROJECT_XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta>
        <project>
          <id>1</id>
          <name>TFG</name>
          <tasks>
            <task><id>1</id><name>clip_a</name><size>4</size></task>
            <task><id>2</id><name>clip_b</name><size>3</size></task>
          </tasks>
        </project>
      </meta>
      <track id="0" label="person" task_id="1">
        <box frame="0" keyframe="1" outside="0" occluded="0"
             xtl="10" ytl="10" xbr="50" ybr="90">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="2" keyframe="1" outside="0" occluded="0"
             xtl="11" ytl="10" xbr="51" ybr="90">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
      </track>
      <track id="0" label="person" task_id="2">
        <box frame="4" keyframe="1" outside="0" occluded="0"
             xtl="20" ytl="20" xbr="60" ybr="99">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">false</attribute>
        </box>
        <box frame="6" keyframe="1" outside="1" occluded="0"
             xtl="21" ytl="20" xbr="61" ybr="99">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">false</attribute>
        </box>
      </track>
    </annotations>
""")

TASK_XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><size>4</size></task></meta>
      <track id="0" label="person">
        <box frame="0" keyframe="1" outside="0" occluded="0"
             xtl="10" ytl="10" xbr="50" ybr="90"/>
      </track>
    </annotations>
""")


def _write(tmp_path, content, name="annotations.xml"):
    p = tmp_path / name
    p.write_text(content)
    return p


def _by_name(parts):
    return {p["name"]: p for p in parts}


def test_rebasea_los_frames_al_espacio_local_de_cada_task(tmp_path):
    # El bug que mata en silencio: sin rebase, clip_b conserva 4 y 6.
    parts = _by_name(split_project_export(_write(tmp_path, PROJECT_XML)))
    doc = parse_cvat_video_xml(_write(tmp_path, parts["clip_b"]["xml"], "b.xml"))
    (track,) = doc["tracks"]
    assert [b["frame"] for b in track["boxes"]] == [0, 2]


def test_cada_salida_lleva_solo_los_tracks_de_su_task(tmp_path):
    parts = _by_name(split_project_export(_write(tmp_path, PROJECT_XML)))
    doc_a = parse_cvat_video_xml(_write(tmp_path, parts["clip_a"]["xml"], "a.xml"))
    assert len(doc_a["tracks"]) == 1
    assert doc_a["tracks"][0]["boxes"][0]["attributes"] == {
        "has_helmet": True, "has_vest": True
    }


def test_emite_meta_task_size_para_que_el_guard_I2_siga_activo(tmp_path):
    # Sin <meta><task><size>, stop_frame queda None y derive_clip_gt deja de
    # comparar el XML contra n_frames del clip preparado.
    parts = _by_name(split_project_export(_write(tmp_path, PROJECT_XML)))
    doc = parse_cvat_video_xml(_write(tmp_path, parts["clip_b"]["xml"], "b.xml"))
    assert doc["stop_frame"] == 2


def test_los_estados_por_frame_quedan_dentro_del_clip(tmp_path):
    # Integración con el consumidor real: la violación de clip_b tiene que
    # aparecer en los frames 0..1 locales, no perderse fuera de rango.
    parts = _by_name(split_project_export(_write(tmp_path, PROJECT_XML)))
    doc = parse_cvat_video_xml(_write(tmp_path, parts["clip_b"]["xml"], "b.xml"))
    states = attribute_states(doc["tracks"][0], "has_helmet", end_frame=2)
    assert states == [False, False, None]


def test_reporta_offset_y_size_de_cada_task(tmp_path):
    parts = _by_name(split_project_export(_write(tmp_path, PROJECT_XML)))
    assert (parts["clip_a"]["offset"], parts["clip_a"]["size"]) == (0, 4)
    assert (parts["clip_b"]["offset"], parts["clip_b"]["size"]) == (4, 3)


def test_filtra_por_nombre_de_task(tmp_path):
    parts = split_project_export(_write(tmp_path, PROJECT_XML), only={"clip_b"})
    assert [p["name"] for p in parts] == ["clip_b"]


def test_el_filtro_rechaza_nombres_inexistentes(tmp_path):
    # Un typo en el clip_id no debe devolver menos clips en silencio.
    with pytest.raises(ValueError, match="no existen en el export.*clip_z"):
        split_project_export(_write(tmp_path, PROJECT_XML), only={"clip_b", "clip_z"})


def test_rechaza_un_export_a_nivel_task(tmp_path):
    with pytest.raises(ValueError, match="no es un export de PROYECTO"):
        split_project_export(_write(tmp_path, TASK_XML, "task.xml"))


def test_rechaza_cajas_fuera_de_la_ventana_de_su_task(tmp_path):
    # Si el modelo de offset no aplicara (otra versión de CVAT, export ya
    # rebaseado), rebasar igual correría los frames a negativo. Mejor romper.
    xml = PROJECT_XML.replace('<box frame="4"', '<box frame="1"')
    with pytest.raises(ValueError, match="fuera de la ventana"):
        split_project_export(_write(tmp_path, xml, "bad.xml"))
