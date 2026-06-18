# e-ovrt_datasets — E-OVRT-VDP Dataset Pipeline

Repositorio de adquisición, validación y conversión de datasets para la plataforma experimental **E-OVRT-VDP** (Experimental Open-Vocabulary Real-Time Video Detection Platform). Proyecto Integrador de Ingeniería en Informática — IUA Córdoba.

El pipeline produce los datasets de entrenamiento y evaluación que consume `e-ovrt_media-plane`. Ambos repositorios deben estar como sibling directories para que los paths relativos de los configs de dataset funcionen correctamente.

---

## Vocabulario canónico v2

Las clases activas son: `person`, `helmet`, `vest`, `bare_head`.

> Los datasets v1 (SH17, SHEL5K, Construction-PPE con vocabulario `no_helmet`/`no_vest`) están en `legacy/`. No usar.

## Datasets v2

| Dataset | Rol | Estado |
|---|---|---|
| construction_site_safety v27 | TRAIN + BENCH | Descargado y convertido |
| chv | TRAIN + DEMO | Descargado y convertido |
| ppe_siabar v1 | TRAIN | Descargado y convertido |
| construction_safety_hardhat | — | Descartado (URL inválida) |

**Conteos (canonical_v2):** TRAIN=5540 imgs, BENCH=196 imgs, DEMO=1064 imgs.

## Comandos principales

```bash
# Descargar datasets v2 (requiere ROBOFLOW_API_KEY para css y ppe_siabar)
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_construction_site_safety.sh
datasets/scripts/download/download_chv.sh
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_ppe_siabar.sh

# Validar descarga
datasets/scripts/validate/summarize_raw_dataset.sh

# Convertir a canonical_v2 (COCO + YOLO + ODVG)
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety chv ppe_siabar \
    --views canonical_v2

# Generar manifests de rol TRAIN/BENCH/DEMO
python3 datasets/scripts/curate/build_role_views.py

# Construir GT persona-nivel del BENCH
python3 datasets/scripts/bench/build_person_gt.py

# Evaluar un run del media-plane contra el BENCH
python3 datasets/scripts/bench/evaluate_bench.py \
    --detections ../e-ovrt_media-plane/runs/<run_id>/detections.jsonl \
    --bench-coco datasets/processed/coco/bench/construction_site_safety_bench.json \
    --person-gt datasets/processed/coco/bench/person_gt.json
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
    curate/          # build_role_views.py, leakage_check.py
    selection/       # quality_sample.py
    bench/           # geometry.py, build_person_gt.py, evaluate_bench.py
  splits/
    v2/              # Manifests activos: train.txt, bench.txt, demo.txt, manifest.json
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
