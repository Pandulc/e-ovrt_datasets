"""Tests de las correcciones de identidad (fixture sintética, revisión dirigida 2026-10).

El caso real que motivó la herramienta: una persona se saca el casco, otra se le cruza
adelante, la anotación la parte en varias trayectorias y la regla C1 de `derive_clip_gt`
(persistencia POR trayectoria) parte o borra el episodio. Lo que se prueba:

  1. `reassign` + `fill` reconstruyen UNA trayectoria y la infracción queda continua;
  2. la normalización cierra cada tramo visible (un tramo movido no queda «vivo»);
  3. los guards: conteos declarados, dos cajas de la misma persona en un cuadro, `fill`
     que no pisa cajas visibles, ceremonia completa;
  4. idempotencia y `--check`.
"""
import textwrap
import xml.etree.ElementTree as ET

import pytest
import yaml

from videogt.apply_identity_corrections import IdentityError, apply_identity, main
from videogt.cvat_xml import attribute_states, parse_cvat_video_xml


def _box(f, helmet, vest="true", outside=0, x=100.0):
    return (f'<box frame="{f}" keyframe="1" outside="{outside}" occluded="0" xtl="{x:.2f}" ytl="50.00" '
            f'xbr="{x + 40:.2f}" ybr="150.00" z_order="0"><attribute name="has_helmet">{helmet}</attribute>'
            f'<attribute name="has_vest">{vest}</attribute></box>')


def _track(tid, boxes):
    return f'<track id="{tid}" label="person" source="manual">' + "".join(boxes) + "</track>"


# 20 cuadros (0..19). P: track 1 (f0-f4, se saca el casco en f2) → tapado f5-f7 → track 2
# (f8-f9) → tapado f10-f11 → track 3 (f12-f19). Track 4: caja suelta en f15 SIN cierre.
# Track 5: Q, con casco todo el clip.
XML = textwrap.dedent(f"""\
    <annotations><version>1.1</version>
    <meta><task><id>1</id><name>clip_t</name><size>20</size></task></meta>
    {_track(1, [_box(0, 'true', x=100), _box(1, 'true', x=102), _box(2, 'false', x=104), _box(3, 'false', x=106),
                _box(4, 'false', x=108), _box(5, 'false', outside=1, x=108)])}
    {_track(2, [_box(8, 'false', x=116), _box(9, 'false', x=118), _box(10, 'false', outside=1, x=118)])}
    {_track(3, [_box(f, 'false', x=124 + 2 * (f - 12)) for f in range(12, 20)])}
    {_track(4, [_box(15, 'false', x=300)])}
    {_track(5, [_box(f, 'true', x=500) for f in range(0, 20)])}
    </annotations>
""")

FIRMA = {"decided_by": "revisor", "decided_at": "2026-10-26", "rationale": "revisión visual"}
MERGE = [
    {"op": "reassign", "from_track": 2, "to_track": 1, "from_frame": 8, "to_frame": 9, "boxes": 2, **FIRMA},
    {"op": "reassign", "from_track": 3, "to_track": 1, "from_frame": 12, "to_frame": 19, "boxes": 8, **FIRMA},
    {"op": "fill", "track": 1, "from_frame": 5, "to_frame": 7,
     "values": {"has_helmet": "false", "has_vest": "true"}, **FIRMA},
    {"op": "fill", "track": 1, "from_frame": 10, "to_frame": 11,
     "values": {"has_helmet": "false", "has_vest": "true"}, **FIRMA},
]


@pytest.fixture()
def paths(tmp_path):
    x = tmp_path / "clip_t.xml"
    x.write_text(XML)
    return x, tmp_path / "clip_t.clip.yaml"


def _yaml(path, ops):
    path.write_text(yaml.safe_dump({"clip_id": "clip_t", "annotation": {"identity_corrections": ops}}))


def _track_states(xml_path, tid, attr="has_helmet"):
    parsed = parse_cvat_video_xml(xml_path)
    tr = next(t for t in parsed["tracks"] if t["track_id"] == tid)
    return attribute_states(tr, attr, parsed["stop_frame"])


def _ids(xml_path):
    return {int(t.get("id")) for t in ET.parse(str(xml_path)).getroot().findall("track")}


def test_reassign_mueve_las_cajas_y_cierra_el_tramo(paths):
    x, y = paths
    _yaml(y, MERGE[:1])
    apply_identity(x, y)
    assert 2 not in _ids(x)                       # el origen quedó vacío y se elimina
    s = _track_states(x, 1)
    assert s[4] is False and s[5] is None and s[7] is None   # el hueco sigue siendo hueco
    assert s[8] is False and s[9] is False
    assert s[10] is None and s[19] is None       # cerrado después del tramo movido


def test_reassign_mas_fill_deja_la_infraccion_continua(paths):
    x, y = paths
    _yaml(y, MERGE)
    r = apply_identity(x, y)
    assert r["aplicadas"] == 4
    s = _track_states(x, 1)
    assert s[0] is True and s[1] is True
    assert all(v is False for v in s[2:20])       # una sola corrida de 18 cuadros
    assert _ids(x) == {1, 4, 5}


def test_fill_marca_occluded_e_interpola_la_geometria(paths):
    x, y = paths
    _yaml(y, MERGE)
    apply_identity(x, y)
    t1 = next(t for t in ET.parse(str(x)).getroot().findall("track") if t.get("id") == "1")
    b6 = next(b for b in t1.findall("box") if b.get("frame") == "6")
    assert b6.get("occluded") == "1" and b6.get("outside") == "0"
    assert float(b6.get("xtl")) == pytest.approx(108 + (116 - 108) * (6 - 4) / (8 - 4))


def test_fill_sin_oclusion_extiende_el_comienzo_de_una_trayectoria(paths):
    """La persona ya se ve entrando y la caja empezaba tarde: se extiende hacia atrás."""
    x, y = paths
    _yaml(y, [{"op": "fill", "track": 2, "from_frame": 6, "to_frame": 7, "occluded": False,
               "values": {"has_helmet": "false", "has_vest": "unknown"}, **FIRMA}])
    apply_identity(x, y)
    s = _track_states(x, 2)
    assert s[5] is None and s[6] is False and s[7] is False and s[9] is False
    t2 = next(t for t in ET.parse(str(x)).getroot().findall("track") if t.get("id") == "2")
    assert {b.get("occluded") for b in t2.findall("box") if b.get("frame") in ("6", "7")} == {"0"}
    assert _track_states(x, 2, "has_vest")[6] is None   # 'unknown' no fabrica nada


def test_es_idempotente(paths):
    x, y = paths
    _yaml(y, MERGE)
    apply_identity(x, y)
    antes = x.read_bytes()
    r2 = apply_identity(x, y)
    assert r2["aplicadas"] == 0 and r2["ya_estaban"] == 4
    assert x.read_bytes() == antes


def test_reasignar_dentro_del_rango_de_otra_reasignacion_es_idempotente(tmp_path):
    """Caso real (a_p7_c03): una caja suelta llena el hueco de una trayectoria ya reasignada.
    Al re-correr, el destino tiene MÁS cajas en ese rango que las declaradas por la primera."""
    x = tmp_path / "h.xml"
    x.write_text(textwrap.dedent(f"""\
        <annotations><version>1.1</version><meta><task><id>1</id><name>h</name><size>20</size></task></meta>
        {_track(1, [_box(f, 'false') for f in range(0, 10)] + [_box(10, 'false', outside=1)])}
        {_track(3, [_box(f, 'false') for f in (12, 13, 14)] + [_box(15, 'false', outside=1)]
                   + [_box(f, 'false') for f in range(16, 20)])}
        {_track(4, [_box(15, 'false', x=300)])}
        </annotations>"""))
    y = tmp_path / "h.clip.yaml"
    _yaml(y, [{"op": "reassign", "from_track": 3, "to_track": 1, "from_frame": 12, "to_frame": 19, "boxes": 7, **FIRMA},
              {"op": "reassign", "from_track": 4, "to_track": 1, "from_frame": 15, "to_frame": 15, "boxes": 1, **FIRMA}])
    apply_identity(x, y)
    antes = x.read_bytes()
    r2 = apply_identity(x, y)
    assert r2["aplicadas"] == 0 and r2["ya_estaban"] == 2
    assert x.read_bytes() == antes
    assert all(v is False for v in _track_states(x, 1)[12:20])


def test_corta_si_el_conteo_no_coincide(paths):
    x, y = paths
    _yaml(y, [{**MERGE[0], "boxes": 3}])
    with pytest.raises(IdentityError, match="se declararon 3"):
        apply_identity(x, y)


def test_corta_si_quedarian_dos_cajas_de_la_misma_persona_en_un_cuadro(paths):
    x, y = paths
    _yaml(y, [{"op": "reassign", "from_track": 5, "to_track": 1, "from_frame": 0, "to_frame": 4, "boxes": 5, **FIRMA}])
    with pytest.raises(IdentityError, match="ya tiene cajas visibles"):
        apply_identity(x, y)


def test_fill_no_pisa_cajas_visibles(paths):
    x, y = paths
    _yaml(y, [{"op": "fill", "track": 1, "from_frame": 3, "to_frame": 6,
               "values": {"has_helmet": "false", "has_vest": "true"}, **FIRMA}])
    with pytest.raises(IdentityError, match="solo rellena huecos"):
        apply_identity(x, y)


def test_close_cierra_la_caja_suelta(paths):
    x, y = paths
    assert _track_states(x, 4)[19] is False       # sin cierre, vale hasta el final del clip
    _yaml(y, [{"op": "close", "track": 4, **FIRMA}])
    apply_identity(x, y)
    s = _track_states(x, 4)
    assert s[15] is False and s[16] is None and s[19] is None


def test_drop_elimina_y_es_idempotente(paths):
    x, y = paths
    _yaml(y, [{"op": "drop", "track": 4, "boxes": 1, **FIRMA}])
    apply_identity(x, y)
    assert 4 not in _ids(x)
    assert apply_identity(x, y)["ya_estaban"] == 1


def test_reasignar_el_final_de_una_trayectoria_cierra_el_origen(tmp_path):
    """Intercambio de identidades: la cola de B es en realidad A. B no puede quedar viva."""
    x = tmp_path / "swap.xml"
    x.write_text(textwrap.dedent(f"""\
        <annotations><version>1.1</version><meta><task><id>1</id><name>s</name><size>20</size></task></meta>
        {_track(1, [_box(f, 'false') for f in range(0, 10)] + [_box(10, 'false', outside=1)])}
        {_track(2, [_box(f, 'true', x=400) for f in range(0, 20)])}
        </annotations>"""))
    y = tmp_path / "swap.clip.yaml"
    _yaml(y, [{"op": "reassign", "from_track": 2, "to_track": 1, "from_frame": 10, "to_frame": 19, "boxes": 10, **FIRMA}])
    apply_identity(x, y)
    b = _track_states(x, 2)
    assert b[9] is True and b[10] is None and b[19] is None
    a = _track_states(x, 1)
    assert a[9] is False and a[10] is True       # el valor que traían las cajas movidas


@pytest.mark.parametrize("faltante", ["decided_by", "decided_at", "rationale", "boxes"])
def test_exige_la_ceremonia_completa(paths, faltante):
    x, y = paths
    op = {k: v for k, v in MERGE[0].items() if k != faltante}
    _yaml(y, [op])
    with pytest.raises(IdentityError, match="faltan campos obligatorios"):
        apply_identity(x, y)


def test_sin_correcciones_es_noop(paths):
    x, y = paths
    y.write_text(yaml.safe_dump({"clip_id": "clip_t"}))
    antes = x.read_bytes()
    assert apply_identity(x, y)["correcciones"] == 0
    assert x.read_bytes() == antes


def test_check_detecta_lo_que_falta_y_no_escribe(paths):
    x, y = paths
    _yaml(y, MERGE)
    antes = x.read_bytes()
    assert main(["--xml", str(x), "--clip-yaml", str(y), "--check"]) == 1
    assert x.read_bytes() == antes
    assert main(["--xml", str(x), "--clip-yaml", str(y)]) == 0
    assert main(["--xml", str(x), "--clip-yaml", str(y), "--check"]) == 0
