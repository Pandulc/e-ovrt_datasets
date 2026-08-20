# e-ovrt_datasets — E-OVRT-VDP Dataset Pipeline

Repositorio de adquisición, validación y conversión de datasets para la plataforma experimental **E-OVRT-VDP** (Experimental Open-Vocabulary Real-Time Video Detection Platform). Proyecto Integrador de Ingeniería en Informática — IUA Córdoba.

El pipeline produce los datasets de entrenamiento y evaluación que consume `e-ovrt_media-plane`. Ambos repositorios deben estar como sibling directories para que los paths relativos de los configs de dataset funcionen correctamente.

---

## Vocabulario canónico v2

Las clases activas son: `person`, `helmet`, `vest`, `bare_head`.

> Los artefactos v1 (vocabulario `no_helmet`/`no_vest`: SH17, Construction-PPE, etc.) están en `legacy/`. No usar. SHEL5K **volvió al pipeline** en 2026-07: hoy es fuente canonical_v2 y estrato de bench_v3.

## Datasets v2

| Dataset | Estado |
|---|---|
| construction_site_safety v27 | Descargado y convertido |
| chv | Descargado y convertido |
| ppe_siabar v1 | Descargado y convertido |
| shel5k (5.000 imgs, Mendeley CC BY 4.0) | Descargado y convertido — estrato de bench_v3 + fuente canonical_v2 |
| construction_safety_hardhat | Descartado (URL inválida) |

> **Histórico:** las vistas por rol TRAIN/BENCH/DEMO (TRAIN=5540, BENCH=196, DEMO=1064) fueron archivadas el 2026-08-15 — estaban huérfanas y cada rol fue superado (BENCH por bench_v3, TRAIN por finetuning_v1, DEMO por el catálogo del media-plane). Ver `datasets/splits/DEPRECATED.md`. **Nunca citar "el BENCH de 196 imágenes" como benchmark vigente.**

## Benchmark de imágenes vigente: `bench_v3`

El benchmark oficial es **`bench_v3` (2026-07-23): 6.477 imágenes estratificadas en 3 fuentes independientes** — `bench_obra` (147, núcleo curado), `chv` (1.330) y `shel5k` (5.000, GT nativo de `bare_head`). Vive congelado en `datasets/processed/coco/bench/curated/bench_v3.json`, con manifest sha-pinned (`bench_v3_manifest.json`). Se regenera con `python3 datasets/scripts/curate/build_bench_v3.py` (idempotente). Provenance y salvedades por estrato: `datasets/registry/bench_v3.md`. **Las métricas se reportan por estrato Y agregadas — nunca solo el agregado.**

## Requisitos

```bash
pip install -r requirements.txt   # Pillow + PyYAML (scripts standalone, sin paquete)
```

Además, por sistema: `ffmpeg` (para `datasets/scripts/videogt/prepare_clip.sh`), `unzip` y `curl` (para los scripts de descarga — `download_chv.sh` requiere `unzip` para extraer). Los download de Roboflow requieren la variable `ROBOFLOW_API_KEY`.

## Comandos principales

```bash
# Descargar datasets v2 (requiere ROBOFLOW_API_KEY para css y ppe_siabar)
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_construction_site_safety.sh
datasets/scripts/download/download_chv.sh
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_ppe_siabar.sh
datasets/scripts/download/download_shel5k.sh

# Validar descarga
datasets/scripts/validate/summarize_raw_dataset.sh

# Convertir a canonical_v2 (COCO + YOLO + ODVG)
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety chv ppe_siabar shel5k \
    --views canonical_v2

# (ARCHIVADO 2026-08-15) Los manifests de rol TRAIN/BENCH/DEMO y su generador
# se movieron a legacy/ — estaban huérfanos y cada rol fue superado.
# Ver datasets/splits/DEPRECATED.md

# Construir GT persona-nivel del BENCH
python3 datasets/scripts/bench/build_person_gt.py

# Evaluar un run del media-plane contra bench_v3 — preferir la CLI del media-plane
# (restringe el GT a las imágenes del run por default):
cd ../e-ovrt_media-plane && .venv/bin/python -m eovrt_media.tools.evaluate \
    --run runs/<run_id> \
    --bench-coco ../e-ovrt_datasets/datasets/processed/coco/bench/curated/bench_v3.json
# (construction_site_safety_bench.json es el BENCH HISTÓRICO de 196 imgs — no usar
#  como benchmark vigente; ver datasets/registry/bench_v3.md)
```

## Estructura

```text
datasets/
  documentation/     # Documentación activa (leer datasets/documentation/README.md)
  registry/          # Metadata, licencias, contrato de anotación, reportes
  raw/               # Imágenes/ZIPs locales — gitignored
  processed/         # COCO, YOLO, ODVG generados — gitignored excepto BENCH GT
  scripts/
    download/        # Scripts de descarga v2
    validate/        # Validación básica de datasets raw
    convert/         # convert_datasets.py → canonical_v2
    curate/          # build_bench_v3.py, build_bench_obra.py, leakage_check.py
    selection/       # quality_sample.py
    bench/           # geometry.py, build_person_gt.py, evaluate_bench.py
  splits/          # DEPRECADO ENTERO (ver DEPRECATED.md); v2/ archivado en legacy/
  tests/             # pytest — sin dependencias de datos raw

legacy/              # Artefactos v1 pre-2026-06-17 (ver legacy/README.md)
```

## Tests

```bash
python3 -m pytest datasets/tests/ -q
```

Los tests no dependen de datos raw; usan fixtures sintéticos.

## Política de versionado

No versionar imágenes, videos ni archives. Versionar: scripts, documentación, registry, anotaciones procesadas necesarias para reproducibilidad (BENCH COCO, person_gt.json).

## Remoto

```text
https://github.com/Pandulc/E-OVRT-VDP.git
```
