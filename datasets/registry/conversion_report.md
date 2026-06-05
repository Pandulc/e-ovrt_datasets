# Conversion Report

Fecha: 2026-06-05

Conversor: `datasets/scripts/convert/convert_datasets.py`

## Formatos generados

- COCO: `datasets/processed/coco/{view}/{dataset_id}/{split}.json`
- YOLO: `datasets/processed/yolo/{view}/{dataset_id}/`
- ODVG: `datasets/processed/odvg/{view}/{dataset_id}/{split}.jsonl`
- Reportes JSON: `datasets/processed/reports/`

## Vistas generadas

- `original`: conserva las clases originales del dataset.
- `canonical_cr01_cr02`: normaliza a `person`, `helmet`, `vest`, `no_helmet`, `no_vest` y descarta clases no mapeadas.

## Resumen validado

| Dataset | Splits | Vista | Imagenes | Anotaciones |
|---|---|---|---:|---:|
| CHV | train/val/test = 1064/133/133 | original | 1330 | 9209 |
| CHV | train/val/test = 1064/133/133 | canonical_cr01_cr02 | 1330 | 9209 |
| SHEL5K | train/val/test = 3500/750/750 | original | 5000 | 75578 |
| SHEL5K | train/val/test = 3500/750/750 | canonical_cr01_cr02 | 5000 | 75578 |
| Construction-PPE | train/val/test = 1132/143/141 | original | 1416 | 11521 |
| Construction-PPE | train/val/test = 1132/143/141 | canonical_cr01_cr02 | 1416 | 6082 |
| SH17 | train/val = 6479/1620 | original | 8099 | 75994 |
| SH17 | train/val = 6479/1620 | canonical_cr01_cr02 | 8099 | 36194 |

## Notas de formato

- COCO usa `bbox` en formato `[x, y, width, height]`.
- YOLO usa `class_id x_center y_center width height`, normalizado a `[0, 1]`.
- ODVG usa JSONL, una imagen por linea, con `detection.instances`; cada instancia usa `bbox` en formato `[x1, y1, x2, y2]`, `label` entero y `category` textual.

## Decisiones

- CHV conserva su split oficial `train/valid/test`; `valid` se normaliza como `val`.
- SHEL5K no trae split oficial; se genero split custom reproducible 70/15/15 con seed 42.
- Construction-PPE conserva su split oficial `train/val/test`.
- SH17 conserva su split oficial `train/val`; no se genero `test` porque el dataset no lo trae.
- En SH17 se usa YOLO como fuente primaria para conversiones, porque los labels YOLO validaron sin cajas fuera de rango y VOC trae 2 cajas fuera de limites.
- Las salidas YOLO generadas referencian rutas absolutas a imagenes raw en `image_lists/{split}.txt`; no duplican imagenes.
