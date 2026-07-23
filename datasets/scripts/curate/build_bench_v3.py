"""Ensambla bench_v3: agregado estratificado de bench_obra + chv + shel5k.

Plan doc 66 §B5 del repo docs. Cada estrato conserva su identidad de fuente
(campo `stratum` en cada imagen) para reportar por-estrato Y agregado; el
manifest declara conteos y sha256 de cada COCO fuente, para congelar el bench
antes de re-evaluar campeones (evita "re-armar en silencio" entre corridas).

Uso:
    python3 datasets/scripts/curate/build_bench_v3.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURATED = ROOT / "processed/coco/bench/curated"

STRATUM_SOURCES = {
    "bench_obra_test": CURATED / "construction_site_safety_bench_obra_test.json",
    "bench_obra_val": CURATED / "construction_site_safety_bench_obra_val.json",
    "chv": CURATED / "bench_stratum_chv.json",
    "shel5k": CURATED / "bench_stratum_shel5k.json",
}


def manifest_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def assemble_bench_v3(strata: dict[str, dict]) -> tuple[dict, dict]:
    """Fusiona COCOs por estrato en un bench_v3 con ids globales únicos.

    Exige que todos los estratos compartan la misma lista de categorías (mismo
    id -> mismo name); si no, es un error de composición, no algo a silenciar.
    Devuelve (bench_v3, manifest) sin tocar los COCOs de entrada.
    """
    stratum_names = list(strata)
    categories = strata[stratum_names[0]]["categories"]
    for name in stratum_names[1:]:
        if strata[name]["categories"] != categories:
            raise ValueError(
                f"categorías inconsistentes entre estratos: '{stratum_names[0]}' vs '{name}'"
            )

    images: list[dict] = []
    annotations: list[dict] = []
    images_by_stratum: dict[str, int] = {}
    next_img_id = next_ann_id = 1

    for name, coco in strata.items():
        remap: dict[int, int] = {}
        for im in coco["images"]:
            remap[im["id"]] = next_img_id
            images.append({**im, "id": next_img_id, "stratum": name})
            next_img_id += 1
        for a in coco["annotations"]:
            annotations.append({**a, "id": next_ann_id, "image_id": remap[a["image_id"]]})
            next_ann_id += 1
        images_by_stratum[name] = len(coco["images"])

    merged = {"images": images, "annotations": annotations, "categories": categories}
    manifest = {
        "strata": stratum_names,
        "images_by_stratum": images_by_stratum,
        "total_images": sum(images_by_stratum.values()),
        "total_annotations": len(annotations),
    }
    return merged, manifest


def main() -> None:
    strata = {}
    source_sha256 = {}
    for name, path in STRATUM_SOURCES.items():
        text = path.read_text()
        source_sha256[name] = manifest_sha256(text)
        strata[name] = json.loads(text)

    merged, manifest = assemble_bench_v3(strata)
    manifest["source_paths"] = {k: str(v.relative_to(ROOT)) for k, v in STRATUM_SOURCES.items()}
    manifest["source_sha256"] = source_sha256
    manifest["bench_v3_sha256"] = manifest_sha256(json.dumps(merged, sort_keys=True))

    out_dir = CURATED
    (out_dir / "bench_v3.json").write_text(json.dumps(merged))
    (out_dir / "bench_v3_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    print(f"bench_v3: {manifest['total_images']} imgs, {manifest['total_annotations']} anns "
          f"| por estrato: {manifest['images_by_stratum']}")


if __name__ == "__main__":
    main()
