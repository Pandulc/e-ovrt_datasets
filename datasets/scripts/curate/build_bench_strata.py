"""Regenera los estratos `chv` y `shel5k` de bench_v3 desde `canonical_v2`.

Cierra un hueco de reproducibilidad: el plan doc 66 §B5 del repo `docs` declara
"COCOs por estrato fusionados (`bench_stratum_{shel5k,chv}.json`, ids remapeados,
basenames verificados únicos)" como paso EJECUTADO, pero hasta 2026-08-19 ningún
script commiteado lo escribía — a diferencia de `bench_obra` (que sí tiene su
generador, `build_bench_obra.py`). Si `bench_v3` hubiera que rearmarlo desde las
fuentes, esos dos estratos eran el eslabón manual de la cadena.

Procedencia REAL, medida sobre los artefactos congelados (no declarada de
memoria) — ver "Verificación" abajo:

- `bench_stratum_chv.json`    = concatenación de `canonical_v2/chv/{train,val,test}.json`
                                (1.064 + 133 + 133 = 1.330 imgs, 9.209 anotaciones)
- `bench_stratum_shel5k.json` = concatenación de `canonical_v2/shel5k/{train,val,test}.json`
                                (3.500 + 750 + 750 = 5.000 imgs, 45.395 anotaciones)

En AMBOS casos: los tres splits se concatenan en el orden `train, val, test`
(el orden importa: fija la asignación de ids); los ids de imagen y de anotación
se remapean a 1..N en ese orden de recorrido; `file_name`, `width`, `height` y
todos los campos de anotación se preservan tal cual vienen de `canonical_v2`;
las claves `info` y `licenses` del COCO fuente se DESCARTAN (los estratos solo
llevan `images`, `annotations`, `categories`, en ese orden); no hay filtrado,
ni muestreo, ni semilla propia — entra el 100% de cada split.

Serialización congelable: `json.dumps(obj)` pelado — separadores por defecto
(`", "` / `": "`), SIN `indent`, SIN `sort_keys`, SIN newline final. Es la que
reproduce byte a byte los archivos del 23-jul (ojo: `build_bench_v3.py` sí usa
`sort_keys=True` para su propia salida; los estratos NO, y cambiarlo rompería el
`source_sha256` del manifest de bench_v3).

Cadena completa (quién produce qué):

    datasets/raw/{chv,shel5k}/...
      └─ convert_datasets.py --views canonical_v2
           └─ processed/coco/canonical_v2/{chv,shel5k}/{train,val,test}.json
                └─ build_bench_strata.py            (ESTE script)
                     └─ curated/bench_stratum_{chv,shel5k}.json
    datasets/processed/coco/bench/construction_site_safety_bench.json
      └─ build_bench_obra.py
           └─ curated/construction_site_safety_bench_obra_{test,val}.json
    los 4 anteriores
      └─ build_bench_v3.py
           └─ curated/bench_v3.json + bench_v3_manifest.json

Verificación (2026-08-19): `--verify` reproduce los DOS estratos congelados byte
a byte (sha256 idéntico) desde `canonical_v2` en disco. No hay parte no
reproducible: no quedó ningún paso manual escondido en la fusión.

Este script NO escribe sobre los artefactos congelados por defecto: sin
`--out-dir` usa un directorio temporal, y escribir dentro de
`processed/coco/bench/curated/` exige `--allow-frozen-overwrite` explícito.

Uso:
    # verificar reproducibilidad contra los congelados (no escribe nada)
    python3 datasets/scripts/curate/build_bench_strata.py --verify

    # regenerar a un directorio propio
    python3 datasets/scripts/curate/build_bench_strata.py --out-dir /tmp/strata

    # regeneración real sobre los congelados (solo si se rearma el bench de cero)
    python3 datasets/scripts/curate/build_bench_strata.py \
        --out-dir datasets/processed/coco/bench/curated --allow-frozen-overwrite
"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_V2 = ROOT / "processed/coco/canonical_v2"
CURATED = ROOT / "processed/coco/bench/curated"

# Orden de concatenación: NO es alfabético ni arbitrario, es el que fija los ids
# 1..N de los artefactos congelados. Cambiarlo cambia todos los ids.
SPLIT_ORDER = ("train", "val", "test")

# estrato -> (directorio canonical_v2 de origen, archivo congelado que produce)
STRATA = {
    "chv": (CANONICAL_V2 / "chv", CURATED / "bench_stratum_chv.json"),
    "shel5k": (CANONICAL_V2 / "shel5k", CURATED / "bench_stratum_shel5k.json"),
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def stratum_payload(fused: dict) -> str:
    """La ÚNICA serialización congelable de un estrato: se hashea y se escribe tal cual.

    `json.dumps` pelado, deliberadamente: es lo que se usó el 23-jul y lo que
    hashea el `source_sha256` del manifest de bench_v3. Ordenar las claves acá
    produciría un archivo distinto y rompería el freeze de bench_v3 aguas abajo.
    """
    return json.dumps(fused)


def fuse_splits(splits: list[dict]) -> dict:
    """Concatena COCOs de un mismo dataset en un estrato con ids 1..N.

    Los splits llegan en el orden de recorrido deseado (`SPLIT_ORDER`); el
    resultado NO depende de nada más (ni semilla, ni filtro, ni muestreo).

    Exige que todos los splits declaren las MISMAS categorías (mismo id -> mismo
    name): un estrato con vocabularios mezclados sería un error de composición,
    no algo a silenciar. Descarta `info`/`licenses` (metadatos por split que no
    aplican al estrato fusionado). No muta los COCOs de entrada.
    """
    if not splits:
        raise ValueError("no hay splits para fusionar")

    categories = splits[0]["categories"]
    for i, coco in enumerate(splits[1:], start=1):
        if coco["categories"] != categories:
            raise ValueError(
                f"categorías inconsistentes entre splits: índice 0 vs índice {i}"
            )

    images: list[dict] = []
    annotations: list[dict] = []
    next_img_id = next_ann_id = 1

    for coco in splits:
        remap: dict[int, int] = {}
        for im in coco["images"]:
            remap[im["id"]] = next_img_id
            images.append({**im, "id": next_img_id})
            next_img_id += 1
        for a in coco["annotations"]:
            annotations.append({**a, "id": next_ann_id, "image_id": remap[a["image_id"]]})
            next_ann_id += 1

    return {"images": images, "annotations": annotations, "categories": categories}


def assert_unique_basenames(fused: dict) -> None:
    """Los basenames deben ser únicos dentro del estrato (doc 66 §B5).

    `build_bench_v3.py` fusiona por referencia y la evaluación del media-plane
    matchea GT contra detecciones POR BASENAME: dos imágenes distintas con el
    mismo basename harían colisionar el GT en silencio.
    """
    basenames = [im["file_name"].split("/")[-1] for im in fused["images"]]
    if len(set(basenames)) != len(basenames):
        seen: set[str] = set()
        dupes = sorted({b for b in basenames if b in seen or seen.add(b)})
        raise ValueError(f"basenames duplicados dentro del estrato: {dupes[:10]}")


def load_splits(source_dir: Path, split_order: tuple[str, ...] = SPLIT_ORDER) -> list[dict]:
    """Lee los COCOs `canonical_v2` de un dataset, en el orden de concatenación."""
    missing = [s for s in split_order if not (source_dir / f"{s}.json").exists()]
    if missing:
        raise FileNotFoundError(
            f"faltan splits canonical_v2 en {source_dir}: {missing} "
            "(regenerar con convert_datasets.py --views canonical_v2)"
        )
    return [json.loads((source_dir / f"{s}.json").read_text()) for s in split_order]


def build_stratum(source_dir: Path) -> dict:
    """Estrato listo para serializar, con las invariantes ya verificadas."""
    fused = fuse_splits(load_splits(source_dir))
    assert_unique_basenames(fused)
    return fused


def _verify(names: list[str]) -> int:
    """Regenera en memoria y compara sha256 contra los congelados. Devuelve exit code."""
    failures = 0
    for name in names:
        source_dir, frozen = STRATA[name]
        if not frozen.exists():
            print(f"[SKIP] {name}: no está el artefacto congelado {frozen}")
            continue
        if not source_dir.exists():
            print(f"[SKIP] {name}: no está la fuente canonical_v2 {source_dir}")
            continue
        payload = stratum_payload(build_stratum(source_dir))
        got, want = sha256_text(payload), hashlib.sha256(frozen.read_bytes()).hexdigest()
        if got == want:
            print(f"[PASS] {name}: sha256 {got} — reproduce byte a byte {frozen.name}")
        else:
            failures += 1
            print(f"[FAIL] {name}: regenerado {got} != congelado {want} ({frozen.name})")
    return 1 if failures else 0


def _write(names: list[str], out_dir: Path, allow_frozen: bool) -> None:
    if out_dir.resolve() == CURATED.resolve() and not allow_frozen:
        raise SystemExit(
            f"negado: {out_dir} es el directorio de artefactos CONGELADOS de bench_v3. "
            "Usá --out-dir a otro lado, o --allow-frozen-overwrite si de verdad "
            "estás rearmando el bench de cero."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        source_dir, frozen = STRATA[name]
        fused = build_stratum(source_dir)
        payload = stratum_payload(fused)
        out = out_dir / frozen.name
        out.write_text(payload)
        print(f"{name}: {len(fused['images'])} imgs, {len(fused['annotations'])} anns "
              f"| sha256 {sha256_text(payload)} -> {out}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Regenera los estratos chv/shel5k de bench_v3 desde canonical_v2."
    )
    p.add_argument("--strata", nargs="+", choices=sorted(STRATA), default=sorted(STRATA),
                   help="Estratos a regenerar (default: todos)")
    p.add_argument("--verify", action="store_true",
                   help="No escribe: regenera en memoria y compara sha256 contra los congelados")
    p.add_argument("--out-dir", type=Path, default=None,
                   help="Destino de la regeneración (default: directorio temporal)")
    p.add_argument("--allow-frozen-overwrite", action="store_true",
                   help="Permite escribir dentro de processed/coco/bench/curated/ (freeze)")
    args = p.parse_args()

    if args.verify:
        raise SystemExit(_verify(args.strata))

    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="bench_strata_"))
    _write(args.strata, out_dir, args.allow_frozen_overwrite)


if __name__ == "__main__":
    main()
