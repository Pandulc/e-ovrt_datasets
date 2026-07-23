"""Curación bench_obra: filtra la contaminación de dominio del BENCH v2.

Auditoría S0 (docs/operacion/63 del repo docs, 2026-07-23): el BENCH mezcla
selfies COVID, PASCAL VOC, aeropuerto/casino/karting (~25%), y tiene bboxes
bare_head sub-pixel. El sub-split obra excluye por regla de prefijo + área
mínima, de forma reproducible.
"""
from curate.build_bench_obra import filter_obra, EXCLUDED_PREFIXES, MIN_BBOX_AREA_PX


def _coco():
    imgs = [
        {"id": 1, "file_name": "datasets/raw/x/test/images/youtube-70_jpg.rf.aaa.jpg",
         "width": 640, "height": 480},
        {"id": 2, "file_name": "datasets/raw/x/test/images/IMG_3100_mp4-1_jpg.rf.bbb.jpg",
         "width": 640, "height": 480},
        {"id": 3, "file_name": "datasets/raw/x/valid/images/construction-1_jpg.rf.ccc.jpg",
         "width": 640, "height": 480},
        {"id": 4, "file_name": "datasets/raw/x/valid/images/2009_000496_jpg.rf.ddd.jpg",
         "width": 640, "height": 480},
    ]
    anns = [
        {"id": 10, "image_id": 1, "category_id": 1, "bbox": [10, 10, 50, 100]},
        {"id": 11, "image_id": 2, "category_id": 1, "bbox": [10, 10, 50, 100]},
        {"id": 12, "image_id": 3, "category_id": 2, "bbox": [5, 5, 30, 30]},
        # degenerada: 2x2.5 px = 5 px^2 < MIN_BBOX_AREA_PX, en imagen de dominio
        {"id": 13, "image_id": 3, "category_id": 4, "bbox": [100, 100, 2.0, 2.5]},
        {"id": 14, "image_id": 4, "category_id": 1, "bbox": [10, 10, 50, 100]},
    ]
    cats = [{"id": i, "name": n} for i, n in
            enumerate(("person", "helmet", "vest", "bare_head"), start=1)]
    return {"images": imgs, "annotations": anns, "categories": cats}


def test_excluye_imagenes_por_prefijo():
    obra_test, obra_val, manifest = filter_obra(_coco())
    kept = [i["file_name"] for i in obra_test["images"] + obra_val["images"]]
    assert not any("IMG_3100" in f or "2009_" in f for f in kept)
    assert any("youtube-70" in f for f in kept)
    assert any("construction-1" in f for f in kept)


def test_divide_por_split_de_path():
    obra_test, obra_val, _ = filter_obra(_coco())
    assert [i["id"] for i in obra_test["images"]] == [1]
    assert [i["id"] for i in obra_val["images"]] == [3]


def test_excluye_bboxes_degeneradas_y_conserva_las_sanas():
    _, obra_val, _ = filter_obra(_coco())
    ids = [a["id"] for a in obra_val["annotations"]]
    assert 12 in ids and 13 not in ids


def test_manifest_registra_exclusiones_con_causa():
    _, _, manifest = filter_obra(_coco())
    razones = {e["file_name"].split("/")[-1]: e["reason"] for e in manifest["excluded_images"]}
    assert any(k.startswith("IMG_3100") for k in razones)
    assert all(r == "domain_prefix" for r in razones.values())
    assert manifest["excluded_annotations_min_area"] == 1
    assert manifest["min_bbox_area_px"] == MIN_BBOX_AREA_PX
    assert manifest["excluded_prefixes"] == list(EXCLUDED_PREFIXES)


def test_manifest_declara_deltas_por_clase_respecto_del_original():
    # El original NUNCA se modifica: la curación es un artefacto aparte y el
    # manifiesto debe permitir reconstruir exactamente qué cambió.
    _, _, manifest = filter_obra(_coco())
    assert manifest["class_counts"]["original"] == {
        "person": 3, "helmet": 1, "vest": 0, "bare_head": 1}
    assert manifest["class_counts"]["obra"] == {
        "person": 1, "helmet": 1, "vest": 0, "bare_head": 0}
    assert manifest["images"]["original"] == 4
    assert manifest["images"]["obra"] == 2


def test_el_coco_de_entrada_no_se_muta():
    coco = _coco()
    antes = (len(coco["images"]), len(coco["annotations"]))
    filter_obra(coco)
    assert (len(coco["images"]), len(coco["annotations"])) == antes


def test_las_anotaciones_de_imagenes_excluidas_no_sobreviven():
    obra_test, obra_val, _ = filter_obra(_coco())
    kept_img_ids = {i["id"] for i in obra_test["images"]} | {i["id"] for i in obra_val["images"]}
    for a in obra_test["annotations"] + obra_val["annotations"]:
        assert a["image_id"] in kept_img_ids
