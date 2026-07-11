"""Derivación de episodios desde timelines de atributos (spec §3.3)."""
import hashlib
import json
import re
import textwrap

import pytest

from videogt.derive_clip_gt import (
    _parse_pattern_set,
    assemble_clip_gt,
    classify_intervals,
    derive,
    frame_to_ms,
    load_clip_meta,
    main,
    merge_scene_intervals,
    subject_labels,
    track_condition_intervals,
    violation_intervals,
)


def test_frame_to_ms_redondea():
    assert frame_to_ms(0, 30) == 0
    assert frame_to_ms(30, 30) == 1000
    assert frame_to_ms(1, 30) == 33


def test_violation_intervals_corta_por_none_y_true():
    # F=viola, T=cumple, N=no visible
    states = [True, False, False, None, False, False, True, False]
    got = violation_intervals(states, fps=10)
    assert got == [
        {"start_ms": 100, "end_ms": 300},   # frames 1-2, corta el None
        {"start_ms": 400, "end_ms": 600},   # frames 4-5, corta el True
        {"start_ms": 700, "end_ms": 800},   # frame 7, corre hasta el final
    ]


def test_violation_intervals_sin_violaciones():
    assert violation_intervals([True, True, None], fps=10) == []


def test_track_condition_intervals_mapea_condiciones():
    track = {
        "track_id": 3,
        "label": "person",
        "boxes": [
            {"frame": 0, "outside": False, "occluded": False, "keyframe": True,
             "attributes": {"has_helmet": False, "has_vest": True}},
            {"frame": 2, "outside": False, "occluded": False, "keyframe": True,
             "attributes": {"has_helmet": True, "has_vest": True}},
        ],
    }
    got = track_condition_intervals(track, end_frame=3, fps=10)
    assert got == [
        {"condition_id": "CR-01", "track_id": 3, "start_ms": 0, "end_ms": 200},
    ]


def _iv(cond, start, end, track=0):
    return {"condition_id": cond, "track_id": track, "start_ms": start, "end_ms": end}


def test_merge_scene_fusiona_solapes_de_misma_condicion():
    merged = merge_scene_intervals([
        _iv("CR-01", 1000, 5000, track=0),
        _iv("CR-01", 4000, 9000, track=1),   # solapa → fusión
        _iv("CR-01", 12000, 13000, track=0), # separado
        _iv("CR-02", 2000, 8000, track=1),   # otra condición, no fusiona
    ])
    assert merged == [
        {"condition_id": "CR-01", "start_ms": 1000, "end_ms": 9000, "subjects_in_evidence": 2},
        {"condition_id": "CR-01", "start_ms": 12000, "end_ms": 13000, "subjects_in_evidence": 1},
        {"condition_id": "CR-02", "start_ms": 2000, "end_ms": 8000, "subjects_in_evidence": 1},
    ]


def test_classify_separa_episodios_de_subumbral():
    episodes, sub = classify_intervals(
        [
            {"condition_id": "CR-01", "start_ms": 0, "end_ms": 4000, "subjects_in_evidence": 1},
            {"condition_id": "CR-01", "start_ms": 8000, "end_ms": 9000, "subjects_in_evidence": 1},
        ],
        {"CR-01": 3000, "CR-02": 5000},
    )
    assert len(episodes) == 1 and episodes[0]["end_ms"] == 4000
    assert len(sub) == 1 and "persistencia" in sub[0]["reason"]


def test_c1_scene_dos_tracks_subumbral_solapados_no_fabrican_episodio():
    """C1: umbral por track ANTES de fusionar — el merge no debe fabricar
    un episodio de escena a partir de dos violaciones sub-umbral de tracks
    distintos que solo se solapan en el tiempo (el motor es 1:1 por sujeto,
    no alertaría ninguno de los dos)."""
    raw = [
        _iv("CR-01", 0, 2500, track=0),     # 2500ms < 3000 → sub-umbral
        _iv("CR-01", 2000, 4500, track=1),  # 2500ms < 3000 → sub-umbral, solapa con track 0
    ]
    per_track_episodes, sub = classify_intervals(raw, {"CR-01": 3000, "CR-02": 5000})
    assert per_track_episodes == []
    scene_episodes = merge_scene_intervals(per_track_episodes)
    assert scene_episodes == []
    assert len(sub) == 2
    assert {s["track_id"] for s in sub} == {0, 1}


def test_c1_scene_track_persistente_mas_subumbral_solapado():
    """Un track que sí llega a persistencia + otro sub-umbral solapado →
    un único episodio de escena (del track persistente) y un sub-umbral."""
    raw = [
        _iv("CR-01", 0, 4000, track=0),     # 4000ms ≥ 3000 → episodio por track
        _iv("CR-01", 2000, 4500, track=1),  # 2500ms < 3000 → sub-umbral, solapa
    ]
    per_track_episodes, sub = classify_intervals(raw, {"CR-01": 3000, "CR-02": 5000})
    scene_episodes = merge_scene_intervals(per_track_episodes)
    assert scene_episodes == [
        {"condition_id": "CR-01", "start_ms": 0, "end_ms": 4000, "subjects_in_evidence": 1},
    ]
    assert len(sub) == 1
    assert sub[0]["track_id"] == 1


def test_c1_subumbral_subject_level_lleva_subject_label():
    """El nivel subject no cambia su lógica de umbral, pero sus
    sub_threshold_events deben propagar subject_label (antes se descartaba)."""
    intervals = [{
        "condition_id": "CR-01", "track_id": 5, "start_ms": 0, "end_ms": 1000,
        "subjects_in_evidence": 1, "subject_label": "persona_A",
    }]
    episodes, sub = classify_intervals(intervals, {"CR-01": 3000, "CR-02": 5000})
    assert episodes == []
    assert len(sub) == 1
    assert sub[0]["subject_label"] == "persona_A"


def test_c1_derive_end_to_end_dos_tracks_subumbral_solapados(tmp_path):
    """Reproducción end-to-end del escenario del hallazgo C1: persona A sin
    casco [0,2500ms) y persona B sin casco [2000,4500ms), ambas sub-umbral —
    el GT de escena NO debe fabricar un episodio CR-01."""
    xml = tmp_path / "c1.xml"
    xml.write_text(textwrap.dedent("""\
        <annotations>
          <version>1.1</version>
          <meta><task><size>300</size></task></meta>
          <track id="0" label="person">
            <box frame="0" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
              <attribute name="has_helmet">false</attribute>
              <attribute name="has_vest">true</attribute>
            </box>
            <box frame="75" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
              <attribute name="has_helmet">true</attribute>
              <attribute name="has_vest">true</attribute>
            </box>
          </track>
          <track id="1" label="person">
            <box frame="60" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
              <attribute name="has_helmet">false</attribute>
              <attribute name="has_vest">true</attribute>
            </box>
            <box frame="135" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
              <attribute name="has_helmet">true</attribute>
              <attribute name="has_vest">true</attribute>
            </box>
          </track>
        </annotations>
    """))
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_c1", "file": "clips/cb_lab_c1.mp4", "fps": 30,
        "duration_ms": 10000, "n_frames": 300, "resolution": "1280x720",
        "sha256": "0" * 64,
    }))
    gt = derive(str(xml), str(cy), str(info), {"CR-01": 3000, "CR-02": 5000})
    assert gt["episodes"] == []
    assert gt["negative"] is True
    assert len(gt["sub_threshold_events"]) == 2
    assert {e["track_id"] for e in gt["sub_threshold_events"]} == {0, 1}


def test_subject_labels_ordena_por_track_id():
    tracks = [{"track_id": 7}, {"track_id": 2}]
    assert subject_labels(tracks) == {2: "persona_A", 7: "persona_B"}


def test_subject_labels_mas_de_26_tracks():
    import re

    tracks = [{"track_id": tid} for tid in range(30)]
    labels = subject_labels(tracks)
    assert labels[25] == "persona_Z"
    assert labels[26] == "persona_AA"
    assert labels[27] == "persona_AB"
    assert len(set(labels.values())) == len(labels)  # todas únicas
    assert all(re.fullmatch(r"persona_[A-Z]+", v) for v in labels.values())


def test_assemble_clip_gt_completo():
    clip_meta = {
        "clip_id": "cb_a01_p1_cr01", "block": "A", "scenario": "P1",
        "level": "scene",
        "recording": {"resolution": "1280x720", "distance_band_m": "5-10",
                      "lighting": "natural", "occlusion": "low"},
        "annotation": {"annotator": "a1", "double_annotated": False},
    }
    clip_info = {"fps": 30, "duration_ms": 32000, "file": "clips/cb_a01_p1_cr01.mp4"}
    episodes = [{"condition_id": "CR-01", "start_ms": 4200, "end_ms": 21500,
                 "subjects_in_evidence": 1}]
    gt = assemble_clip_gt(clip_meta, clip_info, episodes, sub_events=[])
    assert gt["schema_version"] == "clip_gt.v2"
    assert gt["negative"] is False
    assert gt["episodes"][0]["id"] == "ep1"
    assert gt["episodes"][0]["level"] == "scene"
    assert gt["duration_ms"] == 32000
    assert gt["annotation"]["start_end_tolerance_ms"] == 500
    # negativo ⇔ sin episodios
    gt_neg = assemble_clip_gt(clip_meta, clip_info, [], [])
    assert gt_neg["negative"] is True and gt_neg["episodes"] == []


def test_assemble_nota_condicion_activa_al_final():
    clip_meta = {"clip_id": "x", "block": "A", "scenario": "P1", "level": "scene",
                 "recording": {}, "annotation": {"annotator": "a1"}}
    clip_info = {"fps": 30, "duration_ms": 10000, "file": "clips/x.mp4"}
    gt = assemble_clip_gt(clip_meta, clip_info,
                          [{"condition_id": "CR-01", "start_ms": 2000, "end_ms": 10000,
                            "subjects_in_evidence": 1}], [])
    assert "final del clip" in gt["episodes"][0]["notes"]


# FIX 1 (auditoría 2026-07-11): identidad en los episodios — el evaluador del
# control-plane exige source_id en episodios scene y subject_key en subject.
def test_fix1_episodio_scene_trae_source_id_default_clip_id():
    clip_meta = {
        "clip_id": "cb_a01_p1_cr01", "block": "A", "scenario": "P1", "level": "scene",
        "recording": {}, "annotation": {"annotator": "a1"},
    }
    clip_info = {"fps": 30, "duration_ms": 32000, "file": "clips/cb_a01_p1_cr01.mp4"}
    episodes = [{"condition_id": "CR-01", "start_ms": 4200, "end_ms": 21500,
                 "subjects_in_evidence": 1}]
    gt = assemble_clip_gt(clip_meta, clip_info, episodes, sub_events=[])
    assert gt["episodes"][0]["source_id"] == "cb_a01_p1_cr01"


def test_fix1_episodio_scene_source_id_override_en_clip_yaml():
    clip_meta = {
        "clip_id": "cb_a01_p1_cr01", "source_id": "custom_source", "block": "A",
        "scenario": "P1", "level": "scene", "recording": {}, "annotation": {"annotator": "a1"},
    }
    clip_info = {"fps": 30, "duration_ms": 32000, "file": "clips/cb_a01_p1_cr01.mp4"}
    episodes = [{"condition_id": "CR-01", "start_ms": 4200, "end_ms": 21500,
                 "subjects_in_evidence": 1}]
    gt = assemble_clip_gt(clip_meta, clip_info, episodes, sub_events=[])
    assert gt["episodes"][0]["source_id"] == "custom_source"


def test_fix1_episodio_subject_trae_subject_key_y_source_id():
    clip_meta = {
        "clip_id": "cb_lab_p2_subject", "block": "A", "scenario": "P2", "level": "subject",
        "recording": {}, "annotation": {"annotator": "a1"},
    }
    clip_info = {"fps": 30, "duration_ms": 10000, "file": "clips/cb_lab_p2_subject.mp4"}
    episodes = [{"condition_id": "CR-01", "start_ms": 0, "end_ms": 10000,
                 "subjects_in_evidence": 1, "subject_label": "persona_B"}]
    gt = assemble_clip_gt(clip_meta, clip_info, episodes, sub_events=[])
    ep = gt["episodes"][0]
    assert ep["subject_key"] == "persona_B"
    assert ep["subject_key"] == ep["subject_label"]
    assert ep["source_id"] == "cb_lab_p2_subject"


# FIX 3 (auditoría 2026-07-11): level inválido en clip.yaml no debe caer
# silenciosamente a "scene".
def test_fix3_level_invalido_en_clip_yaml_da_error_claro(tmp_path):
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE.replace("level: scene", "level: Subject"))
    with pytest.raises(ValueError, match="Subject"):
        load_clip_meta(str(cy))


def test_fix3_level_con_espacio_da_error_claro(tmp_path):
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE.replace("level: scene", "level: ' scene'"))
    with pytest.raises(ValueError):
        load_clip_meta(str(cy))


# FIX 4 (auditoría 2026-07-11): clip.yaml incompleto debe dar error claro.
def test_fix4_clip_yaml_incompleto_lista_campos_faltantes(tmp_path):
    cy = tmp_path / "clip.yaml"
    cy.write_text("clip_id: x\n")
    with pytest.raises(ValueError) as excinfo:
        load_clip_meta(str(cy))
    assert "block" in str(excinfo.value)
    assert "scenario" in str(excinfo.value)


def test_fix4_clip_yaml_recording_no_dict_da_error_claro(tmp_path):
    cy = tmp_path / "clip.yaml"
    cy.write_text("clip_id: x\nblock: A\nscenario: P1\nrecording: not_a_dict\n")
    with pytest.raises(ValueError, match="recording"):
        load_clip_meta(str(cy))


def test_fix4_clip_yaml_valido_no_levanta(tmp_path):
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE)
    clip_meta = load_clip_meta(str(cy))
    assert clip_meta["clip_id"] == "cb_lab_p1"


# FIX 7 (auditoría 2026-07-11): --pattern-set con valor no entero → error de
# CLI legible, no traceback.
def test_fix7_parse_pattern_set_valor_no_entero_da_error_claro():
    with pytest.raises(ValueError, match="CR-01"):
        _parse_pattern_set("CR-01=abc")


def test_fix7_main_pattern_set_invalido_sale_limpio_no_traceback(capsys):
    with pytest.raises(SystemExit):
        main(["--xml", "x.xml", "--clip-yaml", "c.yaml", "--info", "i.json",
              "--out", "o.json", "--pattern-set", "CR-01=abc"])
    err = capsys.readouterr().err
    assert "CR-01" in err


# End-to-end tests
E2E_XML_SCENE = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><size>300</size></task></meta>
      <track id="0" label="person">
        <box frame="0" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="60" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="210" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="240" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="270" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
      </track>
    </annotations>
""")

CLIP_YAML_SCENE = textwrap.dedent("""\
    clip_id: cb_lab_p1
    block: A
    scenario: P1
    level: scene
    recording:
      resolution: 1280x720
      distance_band_m: "5-10"
      lighting: natural
      occlusion: low
    annotation:
      annotator: a1
      double_annotated: false
""")

E2E_XML_SUBJECT = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><size>300</size></task></meta>
      <track id="0" label="person">
        <box frame="0" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="300" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
      </track>
      <track id="1" label="person">
        <box frame="0" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="300" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
      </track>
    </annotations>
""")

CLIP_YAML_SUBJECT = textwrap.dedent("""\
    clip_id: cb_lab_p2_subject
    block: A
    scenario: P2
    level: subject
    recording:
      resolution: 1280x720
      distance_band_m: "5-10"
      lighting: natural
      occlusion: low
    annotation:
      annotator: a1
      double_annotated: false
""")


def test_derive_end_to_end(tmp_path):
    """Scene level: merges violations across tracks, aggregates subjects."""
    xml = tmp_path / "a.xml"
    xml.write_text(E2E_XML_SCENE)
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_p1", "file": "clips/cb_lab_p1.mp4", "fps": 30,
        "duration_ms": 10000, "n_frames": 300, "resolution": "1280x720",
        "sha256": "0" * 64,
    }))
    gt = derive(str(xml), str(cy), str(info), {"CR-01": 3000, "CR-02": 5000})
    # frames 60-209 sin casco a 30fps = 2000-7000ms → episodio (5000ms ≥ 3000)
    # frames 240-269 = 8000-9000ms = 1000ms < 3000 → sub-umbral
    assert len(gt["episodes"]) == 1
    assert gt["episodes"][0] == {
        "id": "ep1", "condition_id": "CR-01", "level": "scene", "source_id": "cb_lab_p1",
        "start_ms": 2000, "end_ms": 7000, "subjects_in_evidence": 1, "notes": "",
    }
    assert len(gt["sub_threshold_events"]) == 1
    assert gt["sub_threshold_events"][0]["start_ms"] == 8000
    assert gt["negative"] is False


def test_derive_end_to_end_subject_level(tmp_path):
    """Subject level: each track produces separate episode with subject label."""
    xml = tmp_path / "b.xml"
    xml.write_text(E2E_XML_SUBJECT)
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SUBJECT)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_p2_subject", "file": "clips/cb_lab_p2_subject.mp4", "fps": 30,
        "duration_ms": 10000, "n_frames": 300, "resolution": "1280x720",
        "sha256": "1" * 64,
    }))
    gt = derive(str(xml), str(cy), str(info), {"CR-01": 3000, "CR-02": 5000})
    # track 0: always has helmet → no CR-01 violation
    # track 1: never has helmet → CR-01 violation frames 0-299 (0-9999ms)
    # at subject level: track 1 produces one episode
    assert len(gt["episodes"]) == 1
    ep = gt["episodes"][0]
    assert ep["condition_id"] == "CR-01"
    assert ep["level"] == "subject"
    assert ep["subject_label"] == "persona_B"  # track 1 (second by id)
    assert ep["subjects_in_evidence"] == 1
    assert gt["negative"] is False


# C2: cero tracks 'person' no debe fabricar un negativo silencioso.
NO_PERSON_XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><size>10</size></task></meta>
      <track id="0" label="Person">
        <box frame="0" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">false</attribute>
        </box>
      </track>
    </annotations>
""")


def _no_person_fixture(tmp_path):
    xml = tmp_path / "no_person.xml"
    xml.write_text(NO_PERSON_XML)
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_no_person", "file": "clips/cb_lab_no_person.mp4", "fps": 30,
        "duration_ms": 333, "n_frames": 10, "resolution": "1280x720",
        "sha256": "0" * 64,
    }))
    return str(xml), str(cy), str(info)


def test_c2_sin_tracks_person_falla_por_default(tmp_path):
    xml, cy, info = _no_person_fixture(tmp_path)
    with pytest.raises(ValueError, match="Person"):
        derive(str(xml), str(cy), str(info), {"CR-01": 3000, "CR-02": 5000})


def test_c2_allow_empty_permite_negativo_intencional(tmp_path):
    xml, cy, info = _no_person_fixture(tmp_path)
    gt = derive(str(xml), str(cy), str(info), {"CR-01": 3000, "CR-02": 5000},
                allow_empty=True)
    assert gt["negative"] is True
    assert gt["episodes"] == []


# I2: el tamaño del XML debe corresponder al n_frames del clip preparado.
def test_i2_falla_si_size_xml_no_coincide_con_n_frames(tmp_path):
    xml = tmp_path / "a.xml"
    xml.write_text(E2E_XML_SCENE.replace("<size>300</size>", "<size>150</size>"))
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_p1", "file": "clips/cb_lab_p1.mp4", "fps": 30,
        "duration_ms": 10000, "n_frames": 300, "resolution": "1280x720",
        "sha256": "0" * 64,
    }))
    with pytest.raises(ValueError, match="150"):
        derive(str(xml), str(cy), str(info), {"CR-01": 3000, "CR-02": 5000})


def test_i2_tolera_desfase_de_un_frame(tmp_path):
    xml = tmp_path / "a.xml"
    xml.write_text(E2E_XML_SCENE.replace("<size>300</size>", "<size>299</size>"))
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_p1", "file": "clips/cb_lab_p1.mp4", "fps": 30,
        "duration_ms": 10000, "n_frames": 300, "resolution": "1280x720",
        "sha256": "0" * 64,
    }))
    # no debe levantar
    derive(str(xml), str(cy), str(info), {"CR-01": 3000, "CR-02": 5000})


# I3: procedencia (provenance) para determinismo auditable.
def test_i3_derive_incluye_provenance(tmp_path):
    xml = tmp_path / "a.xml"
    xml.write_text(E2E_XML_SCENE)
    cy = tmp_path / "clip.yaml"
    cy.write_text(CLIP_YAML_SCENE)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_p1", "file": "clips/cb_lab_p1.mp4", "fps": 30,
        "duration_ms": 10000, "n_frames": 300, "resolution": "1280x720",
        "sha256": "0" * 64,
    }))
    pattern_set_ms = {"CR-01": 3000, "CR-02": 5000}
    gt = derive(str(xml), str(cy), str(info), pattern_set_ms)
    prov = gt["provenance"]
    assert prov["tool"] == "video-gt-lab/derive_clip_gt"
    assert prov["pattern_set_ms"] == pattern_set_ms
    assert re.fullmatch(r"[0-9a-f]{64}", prov["xml_sha256"])
    assert prov["xml_sha256"] == hashlib.sha256(xml.read_bytes()).hexdigest()
