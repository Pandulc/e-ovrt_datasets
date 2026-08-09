"""Tests de las correcciones de atributos explícitos (fixture sintética, doc 108).

El riesgo que cubren es el más serio de todo el laboratorio: este script es el
ÚNICO que pisa un valor explícito del anotador. `apply_adjudications` se niega a
hacerlo por diseño; acá se permite, y lo que lo vuelve seguro son tres guards:

  1. **`previous_value` se verifica**: si el XML dice otra cosa, corta. Sin esto,
     una corrección declarada contra una versión vieja del XML pisaría en silencio
     un valor que el anotador cambió después.
  2. **Idempotencia**: re-correr la cadena no acumula ni falla.
  3. **Rango que no matchea = error**: una corrección firmada que no se aplicó es
     peor que ninguna (mismo criterio que `apply_adjudications`).

Más la ceremonia: los 7 campos son obligatorios, incluida la firma.
"""
import textwrap
import xml.etree.ElementTree as ET

import pytest
import yaml

from videogt.apply_attribute_corrections import CorrectionError, apply_corrections

XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><id>1</id><name>clip_t</name><size>6</size></task></meta>
      <track id="0" label="person">
        <box frame="0" keyframe="1" outside="0" occluded="0" xtl="1" ytl="1" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">false</attribute>
        </box>
        <box frame="1" keyframe="0" outside="0" occluded="0" xtl="1" ytl="1" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">false</attribute>
        </box>
        <box frame="2" keyframe="0" outside="0" occluded="0" xtl="1" ytl="1" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">unknown</attribute>
        </box>
      </track>
    </annotations>
""")

BASE_CORR = {
    "track_id": 0, "attr": "has_vest", "from_frame": 0, "to_frame": 1,
    "previous_value": "false", "value": "true",
    "decided_by": "simonll4", "decided_at": "2026-08-06",
    "rationale": "revisión visual: sí lleva chaleco",
}


@pytest.fixture()
def paths(tmp_path):
    x = tmp_path / "clip_t.xml"
    x.write_text(XML)
    y = tmp_path / "clip_t.clip.yaml"
    return x, y


def _yaml(path, correcciones):
    path.write_text(yaml.safe_dump(
        {"clip_id": "clip_t", "block": "B", "scenario": "P5",
         "annotation": {"attribute_corrections": correcciones}}))


def _vest(xml_path, frame):
    root = ET.parse(str(xml_path)).getroot()
    for b in root.findall("track/box"):
        if int(b.get("frame")) == frame:
            for a in b.findall("attribute"):
                if a.get("name") == "has_vest":
                    return a.text
    return None


def test_aplica_la_correccion(paths):
    x, y = paths
    _yaml(y, [BASE_CORR])
    r = apply_corrections(x, y)
    assert r["cajas_cambiadas"] == 2
    assert _vest(x, 0) == "true" and _vest(x, 1) == "true"
    # fuera del rango no se toca
    assert _vest(x, 2) == "unknown"


def test_es_idempotente(paths):
    x, y = paths
    _yaml(y, [BASE_CORR])
    apply_corrections(x, y)
    r2 = apply_corrections(x, y)          # segunda pasada
    assert r2["cajas_cambiadas"] == 0 and r2["cajas_ya_corregidas"] == 2
    assert _vest(x, 0) == "true"


def test_corta_si_previous_value_no_coincide(paths):
    x, y = paths
    # el XML dice 'false'; declaramos que decía 'unknown'
    _yaml(y, [{**BASE_CORR, "previous_value": "unknown"}])
    with pytest.raises(CorrectionError, match="NO es ni previous_value"):
        apply_corrections(x, y)
    assert _vest(x, 0) == "false"          # no pisó nada


def test_corta_si_el_rango_no_matchea(paths):
    x, y = paths
    _yaml(y, [{**BASE_CORR, "from_frame": 100, "to_frame": 200}])
    with pytest.raises(CorrectionError, match="no matcheó ninguna caja"):
        apply_corrections(x, y)


@pytest.mark.parametrize("faltante", ["track_id", "decided_by", "rationale", "previous_value", "decided_at"])
def test_exige_la_ceremonia_completa(paths, faltante):
    x, y = paths
    corr = {k: v for k, v in BASE_CORR.items() if k != faltante}
    _yaml(y, [corr])
    with pytest.raises(CorrectionError, match="faltan campos obligatorios"):
        apply_corrections(x, y)


def test_rechaza_correccion_que_no_corrige(paths):
    x, y = paths
    _yaml(y, [{**BASE_CORR, "previous_value": "true", "value": "true"}])
    with pytest.raises(CorrectionError, match="no es una corrección"):
        apply_corrections(x, y)


def test_sin_correcciones_es_noop(paths):
    x, y = paths
    y.write_text(yaml.safe_dump({"clip_id": "clip_t", "block": "B", "scenario": "P5"}))
    r = apply_corrections(x, y)
    assert r["correcciones"] == 0 and _vest(x, 0) == "false"


def test_solo_toca_el_track_declarado(tmp_path):
    """El riesgo que motivó el campo: sin scoping, una corrección firmada para un
    sujeto pisa a los demás que comparten el rango de frames."""
    x = tmp_path / "dos_tracks.xml"
    x.write_text(XML.replace("</annotations>", """
      <track id="1" label="person">
        <box frame="0" keyframe="1" outside="0" occluded="0" xtl="20" ytl="1" xbr="29" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">false</attribute>
        </box>
      </track>
    </annotations>"""))
    y = tmp_path / "c.clip.yaml"
    _yaml(y, [BASE_CORR])                      # track_id: 0
    apply_corrections(x, y)
    root = ET.parse(str(x)).getroot()
    por_track = {int(tr.get("id")): [a.text for b in tr.findall("box")
                                     for a in b.findall("attribute")
                                     if a.get("name") == "has_vest" and int(b.get("frame")) == 0]
                 for tr in root.findall("track")}
    assert por_track[0] == ["true"]            # corregido
    assert por_track[1] == ["false"]           # INTACTO


def test_corta_si_el_track_no_existe(paths):
    x, y = paths
    _yaml(y, [{**BASE_CORR, "track_id": 99}])
    with pytest.raises(CorrectionError, match="no existe el track"):
        apply_corrections(x, y)


# ---------------------------------------------------------------------------
# --check: la red de contención de "las anotaciones del repo son la fuente de verdad"
# ---------------------------------------------------------------------------

def test_check_no_escribe_y_detecta_correccion_faltante(paths):
    """El escenario real (2026-08-09): alguien re-exporta de CVAT el XML SIN las
    correcciones firmadas. Sin este chequeo, re-derivar revertiría el GT en silencio."""
    from videogt.apply_attribute_corrections import main
    x, y = paths
    _yaml(y, [BASE_CORR])
    rc = main(["--xml", str(x), "--clip-yaml", str(y), "--check"])
    assert rc == 1                       # la corrección NO está aplicada
    assert _vest(x, 0) == "false"        # y --check NO tocó el archivo


def test_check_pasa_cuando_ya_estan_aplicadas(paths):
    from videogt.apply_attribute_corrections import main
    x, y = paths
    _yaml(y, [BASE_CORR])
    apply_corrections(x, y)              # se aplican de verdad
    assert main(["--xml", str(x), "--clip-yaml", str(y), "--check"]) == 0
    assert _vest(x, 0) == "true"


def test_check_falla_si_el_xml_derivo_a_otra_cosa(paths):
    """Ni previous_value ni value: el XML cambió por debajo. --check reporta y sale 1
    en vez de abortar con traceback."""
    from videogt.apply_attribute_corrections import main
    x, y = paths
    _yaml(y, [{**BASE_CORR, "previous_value": "unknown"}])
    assert main(["--xml", str(x), "--clip-yaml", str(y), "--check"]) == 1
