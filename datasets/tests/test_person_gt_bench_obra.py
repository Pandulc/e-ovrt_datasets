"""person_gt del núcleo curado (bench_obra, 147 imgs) — sincronía con la curación.

Riesgo cerrado (doc 75 §2.1 del repo docs): el person_gt.json histórico (18-jun)
se construyó sobre el BENCH contaminado de 196 imágenes; 46 de sus 111 violadores
CR-01 (41%) viven en las 49 imágenes que la curación del 23-jul descartó. Evaluar
recall CR-01 contra ese GT infla el denominador-espejo ≈2×. El GT vigente del
núcleo es `curated/person_gt_bench_obra.json`, construido SOLO sobre los dos COCOs
curados de bench_obra.

Los tests sintéticos corren siempre; los que pinnean el artefacto real se skippean
si los archivos no están en disco (suite limpia sin datos procesados).
"""
import json
from pathlib import Path

import pytest

from bench.build_person_gt import build_person_gt_payload

REPO = Path(__file__).resolve().parents[1]  # datasets/
BENCH = REPO / "processed/coco/bench"
CURATED = BENCH / "curated"
PERSON_GT_CURADO = CURATED / "person_gt_bench_obra.json"
PERSON_GT_HISTORICO = BENCH / "person_gt.json"
COCOS_CURADOS = [
    CURATED / "construction_site_safety_bench_obra_val.json",
    CURATED / "construction_site_safety_bench_obra_test.json",
]

needs_artifacts = pytest.mark.skipif(
    not (PERSON_GT_CURADO.exists() and all(p.exists() for p in COCOS_CURADOS)),
    reason="artefactos reales del bench curado no presentes (suite sintética)",
)


# ---------------------------------------------------------------------------
# Sintéticos: build_person_gt_payload sobre múltiples COCOs
# ---------------------------------------------------------------------------

def _coco_una_imagen(img_id: int, file_name: str, con_bare_head: bool) -> dict:
    """COCO canonical_v2 mínimo: 1 imagen, 1 persona, bare_head opcional en la cabeza."""
    anns = [{"id": 1, "image_id": img_id, "category_id": 0, "bbox": [0, 0, 100, 200]}]
    if con_bare_head:
        # centro (50, 25) cae en head_region [0, 0, 100, 66.7] → has_helmet=False
        anns.append({"id": 2, "image_id": img_id, "category_id": 3, "bbox": [30, 5, 40, 40]})
    return {
        "images": [{"id": img_id, "file_name": file_name, "width": 100, "height": 200}],
        "annotations": anns,
        "categories": [
            {"id": 0, "name": "person"},
            {"id": 1, "name": "helmet"},
            {"id": 2, "name": "vest"},
            {"id": 3, "name": "bare_head"},
        ],
    }


def test_payload_concatena_records_de_multiples_cocos():
    cocos = [
        _coco_una_imagen(1, "a/uno.jpg", con_bare_head=True),
        _coco_una_imagen(1, "b/dos.jpg", con_bare_head=False),  # mismo id local: no debe colisionar
    ]
    payload = build_person_gt_payload(cocos)
    assert payload["total_persons"] == 2
    assert payload["violators_cr01"] == 1
    assert payload["violators_cr02"] == 0
    assert {r["file_name"] for r in payload["records"]} == {"a/uno.jpg", "b/dos.jpg"}


def test_payload_conserva_contrato_del_person_gt_historico():
    payload = build_person_gt_payload([_coco_una_imagen(7, "x.jpg", con_bare_head=True)])
    assert payload["matching"] == "center_in_bbox"
    assert payload["source_view"] == "canonical_v2"
    rec = payload["records"][0]
    assert rec["file_name"] == "x.jpg"
    assert rec["image_id"] == 7
    assert rec["has_helmet"] is False
    assert rec["has_vest"] is True


# ---------------------------------------------------------------------------
# Artefacto real: person_gt_bench_obra.json vs. COCOs curados (skip si faltan)
# ---------------------------------------------------------------------------

@needs_artifacts
def test_person_gt_curado_solo_contiene_imagenes_del_coco_curado():
    curated_basenames: set[str] = set()
    for path in COCOS_CURADOS:
        coco = json.loads(path.read_text())
        curated_basenames |= {Path(im["file_name"]).name for im in coco["images"]}
    assert len(curated_basenames) == 147  # núcleo curado (doc 63 / curation_bench_obra.md)

    payload = json.loads(PERSON_GT_CURADO.read_text())
    gt_basenames = {Path(r["file_name"]).name for r in payload["records"]}
    fuera_de_curacion = gt_basenames - curated_basenames
    assert fuera_de_curacion == set(), (
        f"person_gt_bench_obra contiene imágenes excluidas por la curación: {sorted(fuera_de_curacion)[:5]}"
    )


@needs_artifacts
def test_conteo_de_violadores_cr01_del_nucleo_curado():
    """60 violadores CR-01 en el núcleo curado (vs 111 del histórico contaminado).

    111 − 46 (en las 49 imágenes excluidas) = 65; − 5 más cuya única evidencia eran
    los 4 bare_head sub-pixel removidos por la regla de área mínima 9 px²
    (curation_bench_obra.md §2, en 2 imágenes conservadas) = 60.
    262 personas == fila `person` de la tabla de curación.
    """
    payload = json.loads(PERSON_GT_CURADO.read_text())
    recomputado = sum(1 for r in payload["records"] if not r["has_helmet"])
    assert payload["violators_cr01"] == recomputado == 60
    assert payload["total_persons"] == len(payload["records"]) == 262


@pytest.mark.skipif(
    not (PERSON_GT_CURADO.exists() and PERSON_GT_HISTORICO.exists()
         and all(p.exists() for p in COCOS_CURADOS)),
    reason="artefactos reales del bench no presentes (suite sintética)",
)
def test_coherencia_con_el_gt_historico_restringido_a_la_curacion():
    """Los violadores del GT curado son subconjunto estricto del histórico.

    Restricción por imagen sola: 111 → 65 (46 violadores del histórico viven en las
    49 imágenes excluidas por contaminación = 41%). Los 5 restantes (65 → 60) se
    explican por los 4 bare_head sub-pixel removidos dentro de imágenes conservadas
    (curation_bench_obra.md §2). Cada violador curado existe, con el mismo
    person_bbox, en el histórico.
    """
    curated_basenames: set[str] = set()
    for path in COCOS_CURADOS:
        coco = json.loads(path.read_text())
        curated_basenames |= {Path(im["file_name"]).name for im in coco["images"]}

    def key(rec: dict) -> tuple:
        return (Path(rec["file_name"]).name, tuple(rec["person_bbox"]))

    historico = json.loads(PERSON_GT_HISTORICO.read_text())
    viol_historico = [r for r in historico["records"] if not r["has_helmet"]]
    viol_en_curadas = {key(r) for r in viol_historico
                       if Path(r["file_name"]).name in curated_basenames}

    curado = json.loads(PERSON_GT_CURADO.read_text())
    viol_curado = {key(r) for r in curado["records"] if not r["has_helmet"]}

    assert len(viol_historico) == 111  # el histórico contaminado, intacto
    assert len(viol_en_curadas) == 65  # restricción por imagen sola
    assert viol_curado <= viol_en_curadas  # nada nuevo aparece en el curado
    assert len(viol_en_curadas - viol_curado) == 5  # bare_head sub-pixel removidos
    # Las pérdidas viven solo en las 2 imágenes con anotaciones editadas por la regla 2.
    assert {k[0] for k in viol_en_curadas - viol_curado} == {
        "ka_01181_png_jpg.rf.154ee4ef254eabd62e316be50470c578.jpg",
        "youtube-152_jpg.rf.9147878e3ddda845e58f7d9c041f1338.jpg",
    }
