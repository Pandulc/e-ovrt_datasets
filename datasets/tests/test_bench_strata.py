"""Reproducibilidad de los estratos `chv` y `shel5k` de bench_v3 (2026-08-19).

El plan doc 66 §B5 del repo `docs` declara la fusión de estos dos estratos como
paso ejecutado, pero no había script commiteado que la hiciera: `bench_v3` no era
regenerable de punta a punta desde las fuentes. `build_bench_strata.py` cierra ese
hueco, y el test que importa es el de byte-identidad: regenerar desde
`canonical_v2` DEBE dar el mismo sha256 que el artefacto congelado del 23-jul —
si no, el `source_sha256` del manifest de bench_v3 dejaría de verificar.

Los tests de artefacto real se skippean si no están en disco ni la fuente
`canonical_v2` (gitignorada, regenerable con `convert_datasets.py`) ni los
congelados: la suite sintética corre limpia sin datos procesados, igual que en
`test_bench_v3_freeze.py`.
"""
import hashlib
import json

import pytest

from curate.build_bench_strata import (
    SPLIT_ORDER,
    STRATA,
    assert_unique_basenames,
    build_stratum,
    fuse_splits,
    sha256_text,
    stratum_payload,
)


def _coco(img_ids, cat_id=0, prefix="x"):
    return {
        "info": {"description": "sintético"},
        "licenses": [],
        "images": [{"id": i, "file_name": f"a/b/{prefix}{i}.jpg", "width": 10, "height": 10}
                   for i in img_ids],
        "annotations": [{"id": 100 + i, "image_id": i, "category_id": cat_id,
                         "bbox": [0, 0, 5, 5], "area": 25, "iscrowd": 0, "segmentation": []}
                        for i in img_ids],
        "categories": [{"id": 0, "name": "person"}, {"id": 1, "name": "helmet"}],
    }


# ---------------------------------------------------------------------------
# Sintético: la fusión concatena, remapea y no inventa nada
# ---------------------------------------------------------------------------

def test_ids_se_remapean_a_1_n_en_orden_de_concatenacion():
    fused = fuse_splits([_coco([7, 8], prefix="p"), _coco([3], prefix="q")])
    assert [im["id"] for im in fused["images"]] == [1, 2, 3]
    assert [a["id"] for a in fused["annotations"]] == [1, 2, 3]


def test_las_anotaciones_siguen_a_su_imagen_tras_el_remapeo():
    fused = fuse_splits([_coco([7, 8], prefix="p"), _coco([7], prefix="q")])
    by_id = {im["id"]: im["file_name"] for im in fused["images"]}
    # la anotación del segundo split apunta a la imagen del segundo split, no a la homónima del primero
    assert by_id[fused["annotations"][2]["image_id"]] == "a/b/q7.jpg"


def test_el_orden_de_concatenacion_cambia_la_asignacion_de_ids():
    """Documenta por qué SPLIT_ORDER es (train, val, test) y no otra cosa."""
    a, b = _coco([1], prefix="p"), _coco([1], prefix="q")
    assert fuse_splits([a, b])["images"][0]["file_name"] != fuse_splits([b, a])["images"][0]["file_name"]


def test_descarta_info_y_licenses_del_coco_fuente():
    fused = fuse_splits([_coco([1])])
    assert list(fused) == ["images", "annotations", "categories"]


def test_no_muta_los_cocos_de_entrada():
    split = _coco([9])
    fuse_splits([split])
    assert split["images"][0]["id"] == 9 and split["annotations"][0]["id"] == 109


def test_categorias_deben_coincidir_entre_splits():
    otra = {**_coco([1]), "categories": [{"id": 0, "name": "otra"}]}
    with pytest.raises(ValueError, match="categor"):
        fuse_splits([_coco([1]), otra])


def test_rechaza_basenames_duplicados_dentro_del_estrato():
    """Colisión de basename = GT que se pisa en silencio al evaluar (match por basename)."""
    fused = fuse_splits([_coco([1], prefix="p"), _coco([1], prefix="p")])
    with pytest.raises(ValueError, match="basenames duplicados"):
        assert_unique_basenames(fused)


def test_serializacion_es_json_pelado_sin_sort_keys_ni_newline():
    """Los estratos NO usan sort_keys (a diferencia de bench_v3.json): cambiarlo rompe el freeze."""
    payload = stratum_payload(fuse_splits([_coco([1])]))
    assert payload.startswith('{"images": [')
    assert not payload.endswith("\n")
    assert payload == json.dumps(json.loads(payload))


def test_la_serializacion_escrita_es_la_que_se_hashea():
    payload = stratum_payload(fuse_splits([_coco([1, 2])]))
    assert sha256_text(payload) == hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Artefacto real congelado: la regeneración debe dar el MISMO sha256
# ---------------------------------------------------------------------------

def _skip_if_missing(name):
    source_dir, frozen = STRATA[name]
    if not frozen.exists():
        pytest.skip(f"estrato congelado {frozen.name} no presente (suite sintética)")
    if not all((source_dir / f"{s}.json").exists() for s in SPLIT_ORDER):
        pytest.skip(f"fuente canonical_v2 de {name} no presente (gitignorada, regenerable)")
    return source_dir, frozen


@pytest.mark.parametrize("name", sorted(STRATA))
def test_regenerar_reproduce_el_estrato_congelado_byte_a_byte(name):
    source_dir, frozen = _skip_if_missing(name)
    payload = stratum_payload(build_stratum(source_dir))
    assert sha256_text(payload) == hashlib.sha256(frozen.read_bytes()).hexdigest(), (
        f"el estrato '{name}' regenerado desde canonical_v2 ya no reproduce el congelado: "
        "cambió la fuente, el orden de splits o la serialización"
    )


@pytest.mark.parametrize("name,imgs,anns", [("chv", 1330, 9209), ("shel5k", 5000, 45395)])
def test_conteos_congelados_por_estrato(name, imgs, anns):
    """Conteos del freeze del 23-jul (doc 66 §B5): 1.330 + 5.000 = 6.330 de las 6.477."""
    _, frozen = _skip_if_missing(name)
    coco = json.loads(frozen.read_text())
    assert (len(coco["images"]), len(coco["annotations"])) == (imgs, anns)
