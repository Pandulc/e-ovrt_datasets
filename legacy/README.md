# legacy/ — Artefactos v1 (pre-2026-06-17)

Este directorio reúne todos los artefactos producidos antes del reinicio v2 del proyecto (2026-06-17). Se conservan por trazabilidad histórica y por si se necesita consultar decisiones previas.

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
| `download/download_sh17_kaggle.py` | Descarga SH17 desde Kaggle. Dataset no seleccionado en v2. |
| `download/download_sh17_pexels.sh` | Descarga imágenes adicionales de SH17 desde Pexels. |
| `download/download_sh17_repo.sh` | Clona el repo SH17. |
| `download/download_shel5k.sh` | Descarga SHEL5K desde Mendeley Data. Dataset no seleccionado en v2. |
| `download/SHEL5K_MANUAL_DOWNLOAD.md` | Instrucciones de descarga manual de SHEL5K. |
| `curate/generate_finetuning_cr01_cr02.py` | Generaba subsets de fine-tuning v1. Reemplazado por `build_role_views.py`. |
| `split/generate_cr01_cr02_views.py` | Generaba la vista `canonical_cr01_cr02`. Reemplazado por `convert_datasets.py --views canonical_v2`. |
| `video_stock/video_stock_poc.py` | POC de descarga y evaluación de videos stock para DEMO. No integrado. |

### `plans/`

| Archivo | Descripción |
|---|---|
| `2026-06-18-reinicio-seleccion-datasets.md` | Plan de implementación ejecutado para el reinicio v2. Todas las tareas completadas (excepto 4.3). |

### `splits/`

| Directorio | Descripción |
|---|---|
| `cr01_cr02/` | Manifiestos v1: `split_manifest.csv`, `view_manifest.csv`, `finetuning_manifest.csv`, etc. Generados con vocabulario `no_helmet`/`no_vest`. Reemplazados por `datasets/splits/v2/`. |
