# legacy/ — Artefactos v1 (pre-2026-06-17) y archivados posteriores

Este directorio reúne los artefactos producidos antes del reinicio v2 del proyecto (2026-06-17), más los archivados el 2026-08-15 (vistas por rol TRAIN/BENCH/DEMO — ver `datasets/splits/DEPRECATED.md`) y el 2026-08-19. Se conservan por trazabilidad histórica y por si se necesita consultar decisiones previas.

**No usar estos archivos como entrada de ningún pipeline activo.** El vocabulario v1 (`person`, `helmet`, `vest`, `no_helmet`, `no_vest`) fue reemplazado por v2 (`person`, `helmet`, `vest`, `bare_head`).

## Contexto del reinicio

El 2026-06-17 se reinició la selección de datasets y el vocabulario canónico. El diseño que justifica el cambio está en:

```
datasets/documentation/2026-06-17-reinicio-seleccion-datasets-design.md
```

## Contenido

### `documentation/`

| Archivo | Descripción |
|---|---|
| `procedimientos_realizados.md` | Log narrativo de acciones ejecutadas en v1 (corte: 2026-06-05). |
| `realineamiento_finetuning_20260610.md` | Análisis de criterios de curado para fine-tuning v1 (2026-06-10). |
| `plan_obtencion_preparacion_datasets_e_ovrt_vdp.md` | Plan original de trabajo para la etapa de datasets, pre-v2. |
| `estrategia_video_stock_evaluacion_pipeline.md` | POC de uso de video stock para evaluar el pipeline (2026-06-16). No integrado al pipeline v2. |

### `scripts/`

| Script | Descripción |
|---|---|
| `download/download_construction_ppe.sh` | Descarga Construction-PPE (Ultralytics). Dataset no seleccionado en v2. |
| `download/download_construction_safety_hardhat.py` | Descarga construction_safety_hardhat desde Kaggle. Descartado (2026-06-17): URL inválida, nunca se descargó. |
| `download/download_sh17_kaggle.py` | Descarga SH17 desde Kaggle. Dataset no seleccionado en v2. |
| `download/download_sh17_pexels.sh` | Descarga imágenes adicionales de SH17 desde Pexels. |
| `download/download_sh17_repo.sh` | Clona el repo SH17. |
| `download/SHEL5K_MANUAL_DOWNLOAD.md` | Instrucciones de descarga manual de SHEL5K. |
| `curate/generate_finetuning_cr01_cr02.py` | Generaba subsets de fine-tuning v1. Su reemplazo (`build_role_views.py`) fue a su vez archivado el 2026-08-15, superado por bench_v3 / finetuning_v1. |
| `curate/build_role_views.py` | Generaba las vistas por rol TRAIN/BENCH/DEMO desde canonical_v2. Archivado el 2026-08-15 (roles huérfanos, superados por bench_v3 / finetuning_v1 / catálogo del media-plane). `datasets/tests/test_balance.py` lo carga por path — no borrar. |
| `split/generate_cr01_cr02_views.py` | Generaba la vista `canonical_cr01_cr02`. Reemplazado por `convert_datasets.py --views canonical_v2`. |
| `video_stock/video_stock_poc.py` | POC de descarga y evaluación de videos stock para DEMO. No integrado. |
| `video_stock/README.md` | Documentación del POC de video stock. |
| `videogt/gen_ficha.py` | Generador de fichas de clip (video-gt-lab). Archivado el 2026-08-19: sin referencias en ningún pipeline ni doc. |

> **Nota (2026-08-19):** `download/download_shel5k.sh` volvió a `datasets/scripts/download/`:
> SHEL5K reingresó al pipeline (fuente canonical_v2 + estrato de 5.000 imgs de bench_v3, doc 66)
> y ese script es su único downloader reproducible.

### `plans/`

| Archivo | Descripción |
|---|---|
| `2026-06-18-reinicio-seleccion-datasets.md` | Plan de implementación ejecutado para el reinicio v2. Todas las tareas completadas (excepto 4.3). |

### `splits/`

| Directorio | Descripción |
|---|---|
| `cr01_cr02/` | Manifiestos v1: `split_manifest.csv`, `view_manifest.csv`, `finetuning_manifest.csv`, etc. Generados con vocabulario `no_helmet`/`no_vest`. Reemplazados por `legacy/splits/v2/` (a su vez archivado). |
| `v2/` | Manifiestos de rol TRAIN/BENCH/DEMO (`train.txt`, `bench.txt`, `demo.txt`, `manifest.json`). Archivados el 2026-08-15: roles huérfanos, superados por bench_v3 / finetuning_v1 / catálogo del media-plane. Ver `datasets/splits/DEPRECATED.md`. |

### `processed_reports/`

| Archivo | Descripción |
|---|---|
| `construction_ppe_conversion_report.json` | Reporte de conversión v1 de Construction-PPE. |
| `sh17_conversion_report.json` | Reporte de conversión v1 de SH17. |
