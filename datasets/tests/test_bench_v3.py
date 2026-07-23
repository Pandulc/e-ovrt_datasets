"""Ensamblado de bench_v3: agregado estratificado de bench_obra + chv + shel5k.

Cada estrato mantiene su propia identidad (fuente declarada por imagen) para que
el reporte de cierre pueda dar métricas por estrato Y agregadas (doc 66 §B5 del
repo docs). El manifest declara sha256 de cada COCO fuente para congelamiento.
"""
from curate.build_bench_v3 import assemble_bench_v3, manifest_sha256


def _coco(img_ids, cat_id=0):
    return {
        "images": [{"id": i, "file_name": f"x/img{i}.jpg", "width": 10, "height": 10}
                   for i in img_ids],
        "annotations": [{"id": 100 + i, "image_id": i, "category_id": cat_id,
                         "bbox": [0, 0, 5, 5]} for i in img_ids],
        "categories": [{"id": 0, "name": "person"}, {"id": 1, "name": "helmet"}],
    }


def test_asigna_ids_globales_unicos_sin_colisionar():
    strata = {"a": _coco([1, 2]), "b": _coco([1, 2, 3])}
    merged, manifest = assemble_bench_v3(strata)
    ids = [im["id"] for im in merged["images"]]
    assert len(ids) == len(set(ids)) == 5
    ann_ids = [a["id"] for a in merged["annotations"]]
    assert len(ann_ids) == len(set(ann_ids)) == 5


def test_cada_imagen_declara_su_estrato_de_origen():
    strata = {"a": _coco([1]), "b": _coco([1])}
    merged, _ = assemble_bench_v3(strata)
    strata_seen = {im["stratum"] for im in merged["images"]}
    assert strata_seen == {"a", "b"}


def test_anotaciones_apuntan_al_id_global_correcto():
    strata = {"a": _coco([5, 6])}
    merged, _ = assemble_bench_v3(strata)
    img_ids = {im["id"] for im in merged["images"]}
    assert all(a["image_id"] in img_ids for a in merged["annotations"])


def test_manifest_declara_conteos_por_estrato():
    strata = {"a": _coco([1, 2]), "b": _coco([1, 2, 3])}
    _, manifest = assemble_bench_v3(strata)
    assert manifest["images_by_stratum"] == {"a": 2, "b": 3}
    assert manifest["total_images"] == 5


def test_categorias_deben_coincidir_entre_estratos():
    strata = {"a": _coco([1]), "b": {**_coco([1]), "categories": [{"id": 0, "name": "otra"}]}}
    import pytest
    with pytest.raises(ValueError, match="categor"):
        assemble_bench_v3(strata)


def test_manifest_sha256_es_determinista():
    import json
    payload = {"images": [], "annotations": []}
    h1 = manifest_sha256(json.dumps(payload, sort_keys=True))
    h2 = manifest_sha256(json.dumps(payload, sort_keys=True))
    assert h1 == h2 and len(h1) == 64
