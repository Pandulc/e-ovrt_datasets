"""Tests de la aplicación de adjudicaciones humanas sobre huecos `unknown` (F-GT1).

Esta es la ÚNICA pieza del laboratorio capaz de convertir incertidumbre en
violación, así que el contrato es restrictivo por diseño: la decisión tiene que
venir declarada, firmada y justificada en `clip.yaml`, y nunca puede pisar una
anotación explícita del humano.
"""
import textwrap

import pytest

from videogt.apply_adjudications import apply_adjudications

# 10 frames, un track: true(0-1) false(2-3) unknown(4-6) false(7-8) true(9)
def _xml(unknown_value="unknown"):
    rows = []
    for f in range(10):
        v = ("true" if f < 2 else "false" if f < 4 else unknown_value
             if f < 7 else "false" if f < 9 else "true")
        rows.append(f"""  <box frame="{f}" keyframe="1" outside="0" occluded="0"
       xtl="10" ytl="10" xbr="50" ybr="90">
    <attribute name="has_helmet">{v}</attribute>
    <attribute name="has_vest">true</attribute>
  </box>""")
    return textwrap.dedent("""\
        <annotations>
          <version>1.1</version>
          <meta><task><size>10</size></task></meta>
          <track id="0" label="person">
        """) + "\n".join(rows) + "\n  </track>\n</annotations>\n"


ADJ = {"attr": "has_helmet", "from_frame": 4, "to_frame": 6, "value": "false",
       "decided_by": "simonll4", "rationale": "sigue sin casco, unknown por oclusión"}


def _setup(tmp_path, adjudications, xml=None):
    x = tmp_path / "c.xml"
    x.write_text(xml or _xml())
    y = tmp_path / "c.clip.yaml"
    import yaml
    y.write_text(yaml.safe_dump({
        "clip_id": "c", "block": "A", "scenario": "P1",
        "annotation": {"unknown_adjudications": adjudications},
    }))
    return x, y


def _states(xml_path, attr="has_helmet"):
    import xml.etree.ElementTree as ET
    root = ET.parse(xml_path).getroot()
    out = []
    for b in root.find("track").findall("box"):
        v = next(a.text for a in b.findall("attribute") if a.get("name") == attr)
        out.append(v)
    return out


def test_reemplaza_unknown_por_el_valor_adjudicado_en_el_rango(tmp_path):
    x, y = _setup(tmp_path, [ADJ])
    r = apply_adjudications(x, y)
    assert r["total_changed"] == 3
    assert _states(x) == ["true", "true", "false", "false",
                          "false", "false", "false", "false", "false", "true"]


def test_no_toca_frames_fuera_del_rango(tmp_path):
    x, y = _setup(tmp_path, [{**ADJ, "from_frame": 5, "to_frame": 5}])
    apply_adjudications(x, y)
    assert _states(x)[4] == "unknown" and _states(x)[6] == "unknown"


def test_no_toca_otros_atributos(tmp_path):
    x, y = _setup(tmp_path, [ADJ])
    apply_adjudications(x, y)
    assert _states(x, "has_vest") == ["true"] * 10


def test_es_idempotente(tmp_path):
    x, y = _setup(tmp_path, [ADJ])
    apply_adjudications(x, y)
    r2 = apply_adjudications(x, y)
    assert r2["total_changed"] == 0
    assert _states(x)[4:7] == ["false"] * 3


def test_se_niega_a_pisar_una_anotacion_explicita_del_humano(tmp_path):
    # El hueco viene anotado 'true': adjudicar 'false' encima sería fabricar
    # una violación sobre evidencia humana contraria.
    x, y = _setup(tmp_path, [ADJ], xml=_xml(unknown_value="true"))
    with pytest.raises(ValueError, match="valor explícito"):
        apply_adjudications(x, y)


def test_rechaza_un_valor_que_no_sea_true_o_false(tmp_path):
    x, y = _setup(tmp_path, [{**ADJ, "value": "unknown"}])
    with pytest.raises(ValueError, match="value"):
        apply_adjudications(x, y)


def test_exige_firma_y_justificacion(tmp_path):
    incompleta = {k: v for k, v in ADJ.items() if k != "rationale"}
    x, y = _setup(tmp_path, [incompleta])
    with pytest.raises(ValueError, match="rationale"):
        apply_adjudications(x, y)


def test_sin_adjudicaciones_no_hace_nada(tmp_path):
    x, y = _setup(tmp_path, [])
    r = apply_adjudications(x, y)
    assert r["total_changed"] == 0
    assert _states(x)[4:7] == ["unknown"] * 3


def test_avisa_si_el_rango_no_coincide_con_ninguna_caja(tmp_path):
    # Un rango mal tipeado (fuera del clip) no debe pasar inadvertido: si no
    # matcheó nada, la adjudicación que el humano firmó no se aplicó.
    x, y = _setup(tmp_path, [{**ADJ, "from_frame": 50, "to_frame": 60}])
    with pytest.raises(ValueError, match="no coincidió con ninguna caja"):
        apply_adjudications(x, y)


def test_el_episodio_queda_unido_al_derivar(tmp_path):
    """La prueba que importa: sin adjudicar hay 2 episodios, con adjudicación 1."""
    import json
    from videogt.derive_clip_gt import derive

    info = tmp_path / "c.info.json"
    info.write_text(json.dumps({"clip_id": "c", "file": "clips/c.mp4", "fps": 1,
                                "duration_ms": 10000, "n_frames": 10,
                                "resolution": "64x64", "sha256": "x"}))
    ps = {"CR-01": 1000, "CR-02": 1000}

    sin_dir = tmp_path / "sin"; sin_dir.mkdir()
    x1, y1 = _setup(sin_dir, [])
    assert len(derive(x1, y1, info, ps)["episodes"]) == 2

    con_dir = tmp_path / "con"; con_dir.mkdir()
    x2, y2 = _setup(con_dir, [ADJ])
    apply_adjudications(x2, y2)
    episodios = derive(x2, y2, info, ps)["episodes"]
    assert len(episodios) == 1
    assert (episodios[0]["start_ms"], episodios[0]["end_ms"]) == (2000, 9000)
