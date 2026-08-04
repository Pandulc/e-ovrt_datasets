"""GT de CR-02 a nivel persona desde negativos EXPLICITOS del raw (Fase D, Nivel A).

Por que existe este modulo (doc 83 del repo docs): la Fase 1 de la Fase D puntua el
estado por persona contra has_helmet/has_vest, pero **has_vest no existia**:
`person_gt_bench_obra.json` lo trae en True para las 262 personas y lo declara como
placeholder (`note_cr02`: "NO-Safety Vest no es clase canonical_v2"), y SHEL5K no
anota chaleco. Sin has_vest real, el gate del pre-registro ("F1 de E-DIR < 50% del de
E-IND en AMBAS condiciones") no puede evaluarse para CR-02.

La clase negativa SI existe en el raw de construction_site_safety (`NO-Safety Vest`,
indice 4): solo se pierde al mapear a canonical_v2. Este modulo la recupera.

**Anti-circularidad D10 — la razon por la que NO se deriva por geometria.** La
alternativa descartada era inferir has_vest desde el estrato CHV: "ninguna caja `vest`
cae dentro de la persona" => sin chaleco. Eso es exactamente la operacion que hace
E-IND (`spatial_absence`). Construir el GT con la logica de E-IND y despues usarlo
para comparar E-DIR contra E-IND le regala la comparacion a E-IND, justo en el eje
central de la tesis. Por eso el GT sale de negativos marcados por un humano, y hay un
test abajo que lo fija.
"""
import json
from pathlib import Path

import pytest

from bench.build_person_gt import build_person_gt_payload
from bench.person_gt_cr02 import (
    build_person_gt_payload_with_raw_negatives,
    load_raw_negative_records,
    yolo_line_to_xyxy,
)

REPO = Path(__file__).resolve().parents[1]  # datasets/
CURATED = REPO / "processed/coco/bench/curated"
RAW_CSS = REPO / "raw/construction_site_safety"
COCOS_CURADOS = [
    CURATED / "construction_site_safety_bench_obra_val.json",
    CURATED / "construction_site_safety_bench_obra_test.json",
]

# Orden de clases del raw (data.yaml de construction_site_safety v27) — el indice
# posicional es el que aparece en los .txt YOLO.
CSS_CLASSES = [
    "Hardhat", "Mask", "NO-Hardhat", "NO-Mask", "NO-Safety Vest",
    "Person", "Safety Cone", "Safety Vest", "machinery", "vehicle",
]
CSS_NEGATIVES = {"NO-Safety Vest": "no_vest"}

needs_raw = pytest.mark.skipif(
    not (RAW_CSS.is_dir() and all(p.exists() for p in COCOS_CURADOS)),
    reason="raw de construction_site_safety no presente (suite sintetica)",
)


# ---------------------------------------------------------------------------
# Conversion YOLO -> xyxy en pixeles
# ---------------------------------------------------------------------------

def test_yolo_line_a_xyxy_centro_ancho_alto_normalizados():
    # centro (0.5, 0.5), tamano (0.2, 0.4) sobre 200x100 -> [80, 30, 120, 70]
    class_id, bbox = yolo_line_to_xyxy("4 0.5 0.5 0.2 0.4", 200, 100)
    assert class_id == 4
    assert bbox == pytest.approx([80.0, 30.0, 120.0, 70.0])


def test_yolo_line_recorta_a_los_bordes_de_la_imagen():
    """Una caja que se sale del frame se recorta, igual que parse_yolo del conversor."""
    _, bbox = yolo_line_to_xyxy("4 0.05 0.05 0.4 0.4", 100, 100)
    assert bbox[0] == 0.0 and bbox[1] == 0.0
    assert bbox[2] == pytest.approx(25.0) and bbox[3] == pytest.approx(25.0)


def test_yolo_line_rechaza_linea_malformada():
    with pytest.raises(ValueError):
        yolo_line_to_xyxy("4 0.5 0.5 0.2", 100, 100)


# ---------------------------------------------------------------------------
# Extraccion de negativos explicitos
# ---------------------------------------------------------------------------

def test_solo_extrae_las_clases_negativas_declaradas(tmp_path):
    label = tmp_path / "img.txt"
    label.write_text(
        "5 0.5 0.5 0.3 0.8\n"      # Person  -> se ignora
        "7 0.5 0.4 0.2 0.2\n"      # Safety Vest (POSITIVO) -> se ignora
        "4 0.5 0.45 0.15 0.15\n"   # NO-Safety Vest -> unico registro
        "2 0.5 0.1 0.1 0.1\n"      # NO-Hardhat -> no esta en negatives de este mapa
    )
    recs = load_raw_negative_records(label, CSS_CLASSES, CSS_NEGATIVES, 100, 100)
    assert len(recs) == 1
    assert recs[0]["flag"] == "no_vest"
    assert recs[0]["condition"] == "CR-02"


def test_label_inexistente_no_es_error(tmp_path):
    """Una imagen sin .txt es una imagen sin anotaciones, no una falla."""
    recs = load_raw_negative_records(tmp_path / "no_existe.txt", CSS_CLASSES, CSS_NEGATIVES, 10, 10)
    assert recs == []


# ---------------------------------------------------------------------------
# Payload completo: CR-01 desde bare_head + CR-02 desde el negativo raw
# ---------------------------------------------------------------------------

def _coco(anns: list[dict], width: int = 100, height: int = 200) -> dict:
    return {
        "images": [{"id": 1, "file_name": "split/images/uno.jpg", "width": width, "height": height}],
        "annotations": anns,
        "categories": [
            {"id": 0, "name": "person"}, {"id": 1, "name": "helmet"},
            {"id": 2, "name": "vest"}, {"id": 3, "name": "bare_head"},
        ],
    }


PERSONA = {"id": 1, "image_id": 1, "category_id": 0, "bbox": [0, 0, 100, 200]}


def test_negativo_raw_dentro_de_la_persona_marca_has_vest_false(tmp_path):
    label = tmp_path / "uno.txt"
    # NO-Safety Vest centrado en (50, 100) sobre 100x200 -> cae dentro de la persona
    label.write_text("4 0.5 0.5 0.2 0.2\n")
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([PERSONA])], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    rec = payload["records"][0]
    assert rec["has_vest"] is False
    assert rec["has_helmet"] is True          # sin bare_head, el casco no se toca
    assert payload["violators_cr02"] == 1


def test_negativo_raw_fuera_de_la_persona_deja_has_vest_true(tmp_path):
    label = tmp_path / "uno.txt"
    # persona ocupa x in [0,100] de una imagen de 400 de ancho: el negativo en x=0.9 cae afuera
    label.write_text("4 0.9 0.5 0.05 0.05\n")
    coco = _coco([{"id": 1, "image_id": 1, "category_id": 0, "bbox": [0, 0, 100, 200]}],
                 width=400, height=200)
    payload = build_person_gt_payload_with_raw_negatives(
        [coco], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    assert payload["records"][0]["has_vest"] is True
    assert payload["violators_cr02"] == 0


def test_las_dos_condiciones_conviven_en_un_mismo_registro(tmp_path):
    label = tmp_path / "uno.txt"
    label.write_text("4 0.5 0.5 0.2 0.2\n")
    bare_head = {"id": 2, "image_id": 1, "category_id": 3, "bbox": [30, 5, 40, 40]}
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([PERSONA, bare_head])], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    rec = payload["records"][0]
    assert rec["has_helmet"] is False and rec["has_vest"] is False
    assert payload["violators_cr01"] == 1 and payload["violators_cr02"] == 1


def test_el_note_cr02_deja_de_declarar_placeholder(tmp_path):
    """El contrato tiene que decir de donde sale has_vest, o el numero se lee mal."""
    label = tmp_path / "uno.txt"
    label.write_text("4 0.5 0.5 0.2 0.2\n")
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([PERSONA])], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    assert "has_vest=True para todos" not in payload["note_cr02"]
    assert "NO-Safety Vest" in payload["note_cr02"]
    assert payload["cr02_source"] == "explicit_raw_negatives"


# ---------------------------------------------------------------------------
# Anti-circularidad D10 — el test que fija la decision
# ---------------------------------------------------------------------------

def test_ausencia_de_caja_vest_positiva_NO_marca_violacion(tmp_path):
    """Sin negativo explicito, una persona sin ninguna caja `vest` sigue con chaleco.

    Este es el invariante D10. Derivar has_vest=False de "no hay caja vest dentro de
    la persona" es la operacion de E-IND (spatial_absence): usarlo como GT haria
    circular la comparacion E-DIR vs E-IND. Si alguien "arregla" esto para subir el n
    de CR-02, rompe el experimento y este test tiene que ponerse en rojo.
    """
    label = tmp_path / "uno.txt"
    label.write_text("5 0.5 0.5 0.3 0.8\n")  # solo Person: ni vest positivo ni negativo
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([PERSONA])], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    assert payload["records"][0]["has_vest"] is True
    assert payload["violators_cr02"] == 0


def test_imagen_sin_label_raw_no_inventa_violaciones(tmp_path):
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([PERSONA])], {}, CSS_CLASSES, CSS_NEGATIVES)
    assert payload["records"][0]["has_vest"] is True


# ---------------------------------------------------------------------------
# Compatibilidad: CR-01 no cambia respecto del builder vigente
# ---------------------------------------------------------------------------

def test_cr01_identico_al_builder_sin_negativos_raw(tmp_path):
    bare_head = {"id": 2, "image_id": 1, "category_id": 3, "bbox": [30, 5, 40, 40]}
    cocos = [_coco([PERSONA, bare_head])]
    base = build_person_gt_payload(cocos)
    nuevo = build_person_gt_payload_with_raw_negatives(cocos, {}, CSS_CLASSES, CSS_NEGATIVES)
    assert base["violators_cr01"] == nuevo["violators_cr01"]
    assert [r["has_helmet"] for r in base["records"]] == [r["has_helmet"] for r in nuevo["records"]]
    assert [r["person_bbox"] for r in base["records"]] == [r["person_bbox"] for r in nuevo["records"]]


# ---------------------------------------------------------------------------
# Artefacto real (skip si el raw no esta en disco)
# ---------------------------------------------------------------------------

@needs_raw
def test_nucleo_curado_conserva_262_personas_y_60_violadores_cr01():
    """El GT de CR-02 se agrega SIN mover CR-01: mismo n, mismos violadores."""
    from bench.person_gt_cr02 import build_bench_obra_payload

    payload = build_bench_obra_payload(COCOS_CURADOS, RAW_CSS)
    assert payload["total_persons"] == 262
    assert payload["violators_cr01"] == 60


@needs_raw
def test_nucleo_curado_tiene_violadores_cr02_reales():
    """Si esto da 0, el GT de CR-02 volvio a ser placeholder y la Fase 1 no puede correr."""
    from bench.person_gt_cr02 import build_bench_obra_payload

    payload = build_bench_obra_payload(COCOS_CURADOS, RAW_CSS)
    assert payload["violators_cr02"] > 0
    recomputado = sum(1 for r in payload["records"] if not r["has_vest"])
    assert payload["violators_cr02"] == recomputado


@needs_raw
def test_violadores_cr02_acotados_por_los_negativos_explicitos_disponibles():
    """No puede haber mas personas sin chaleco que anotaciones NO-Safety Vest.

    Cota superior dura, y el motivo por el que la atribucion es 1:1: sin desambiguar,
    en el nucleo curado salian 148 violadores contra 147 negativos, porque 15 cajas
    caen dentro de DOS personas superpuestas. Cada negativo marca a una sola persona.
    """
    from bench.person_gt_cr02 import build_bench_obra_payload, resolve_label_paths

    payload = build_bench_obra_payload(COCOS_CURADOS, RAW_CSS)
    labels = resolve_label_paths([json.loads(p.read_text()) for p in COCOS_CURADOS], RAW_CSS)
    n_negativos = 0
    for path in labels.values():
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip() and int(line.split()[0]) == CSS_CLASSES.index("NO-Safety Vest"):
                n_negativos += 1
    assert 0 < payload["violators_cr02"] <= n_negativos


@needs_raw
def test_los_casos_ambiguos_quedan_marcados_y_contados():
    """Los 15 negativos que caian en dos personas tienen que ser auditables.

    No se resuelven en silencio: el payload declara cuantos hubo y cada persona
    candidata queda con `vest_attribution_ambiguous`, para que el scorer pueda
    reportar CR-02 con y sin ellas (analisis de sensibilidad que sale gratis).
    """
    from bench.person_gt_cr02 import build_bench_obra_payload

    payload = build_bench_obra_payload(COCOS_CURADOS, RAW_CSS)
    assert payload["cr02_ambiguous_negatives"] == 15
    marcadas = [r for r in payload["records"] if r.get("vest_attribution_ambiguous")]
    # 27 personas distintas, no 30: en las imagenes con multitud la misma pareja de
    # cuerpos superpuestos es candidata de varios negativos a la vez.
    assert len(marcadas) == 27
    assert len(marcadas) <= 2 * payload["cr02_ambiguous_negatives"]


# ---------------------------------------------------------------------------
# Atribucion 1:1 de cada negativo
# ---------------------------------------------------------------------------

def test_negativo_dentro_de_dos_personas_marca_a_una_sola(tmp_path):
    """Dos personas superpuestas, un solo negativo: no puede violar las dos."""
    label = tmp_path / "uno.txt"
    label.write_text("4 0.5 0.5 0.1 0.1\n")   # centro (50, 100) en 100x200
    grande = {"id": 1, "image_id": 1, "category_id": 0, "bbox": [0, 0, 100, 200]}
    chica = {"id": 2, "image_id": 1, "category_id": 0, "bbox": [20, 40, 60, 120]}
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([grande, chica])], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    assert payload["violators_cr02"] == 1
    assert payload["cr02_ambiguous_negatives"] == 1
    # Gana la que contiene mejor al negativo; ante contencion total, la de menor area.
    violadora = [r for r in payload["records"] if not r["has_vest"]][0]
    assert violadora["person_bbox"] == [20.0, 40.0, 80.0, 160.0]
    # Las dos candidatas quedan marcadas, no solo la elegida.
    assert all(r.get("vest_attribution_ambiguous") for r in payload["records"])


def test_negativo_en_una_sola_persona_no_marca_ambiguedad(tmp_path):
    label = tmp_path / "uno.txt"
    label.write_text("4 0.5 0.5 0.1 0.1\n")
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([PERSONA])], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    assert payload["violators_cr02"] == 1
    assert payload["cr02_ambiguous_negatives"] == 0
    assert not payload["records"][0].get("vest_attribution_ambiguous")


def test_dos_negativos_marcan_dos_personas_distintas(tmp_path):
    """La atribucion 1:1 no puede colapsar dos violaciones en una persona."""
    label = tmp_path / "uno.txt"
    label.write_text("4 0.15 0.5 0.06 0.06\n4 0.85 0.5 0.06 0.06\n")
    izq = {"id": 1, "image_id": 1, "category_id": 0, "bbox": [0, 0, 40, 200]}
    der = {"id": 2, "image_id": 1, "category_id": 0, "bbox": [60, 0, 40, 200]}
    payload = build_person_gt_payload_with_raw_negatives(
        [_coco([izq, der])], {"uno.jpg": label}, CSS_CLASSES, CSS_NEGATIVES)
    assert payload["violators_cr02"] == 2
    assert payload["cr02_ambiguous_negatives"] == 0
