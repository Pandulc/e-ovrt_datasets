"""Tests del parser CVAT for video 1.1 (fixture sintético, sin media)."""
import textwrap

from videogt.cvat_xml import attribute_states, parse_cvat_video_xml

CVAT_XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><size>10</size></task></meta>
      <track id="0" label="person" source="semi-auto">
        <box frame="2" keyframe="1" outside="0" occluded="0"
             xtl="10" ytl="10" xbr="50" ybr="90">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="5" keyframe="1" outside="0" occluded="1"
             xtl="12" ytl="10" xbr="52" ybr="90">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="8" keyframe="1" outside="1" occluded="0"
             xtl="12" ytl="10" xbr="52" ybr="90">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
      </track>
    </annotations>
""")


def _write(tmp_path, content):
    p = tmp_path / "annotations.xml"
    p.write_text(content)
    return p


def test_parse_tracks_y_stop_frame(tmp_path):
    doc = parse_cvat_video_xml(_write(tmp_path, CVAT_XML))
    assert doc["stop_frame"] == 9
    (track,) = doc["tracks"]
    assert track["track_id"] == 0 and track["label"] == "person"
    assert [b["frame"] for b in track["boxes"]] == [2, 5, 8]
    assert track["boxes"][0]["attributes"] == {"has_helmet": True, "has_vest": True}
    assert track["boxes"][2]["outside"] is True
    assert track["boxes"][1]["occluded"] is True


def test_attribute_states_escalon_y_outside(tmp_path):
    doc = parse_cvat_video_xml(_write(tmp_path, CVAT_XML))
    states = attribute_states(doc["tracks"][0], "has_helmet", end_frame=9)
    # frames 0-1: aun no aparece; 2-4: true; 5-7: false; 8-9: outside
    assert states == [None, None, True, True, True, False, False, False, None, None]


def test_atributo_ausente_es_none(tmp_path):
    xml = CVAT_XML.replace('<attribute name="has_vest">true</attribute>', "")
    doc = parse_cvat_video_xml(_write(tmp_path, xml))
    states = attribute_states(doc["tracks"][0], "has_vest", end_frame=4)
    assert states[3] is None  # atributo faltante NO fabrica violación
