# Guia de conversiones COCO, YOLO y ODVG

Fecha de corte: 2026-06-05

## Script principal

```bash
datasets/scripts/convert/convert_datasets.py --datasets chv shel5k construction_ppe sh17
```

Tambien se puede convertir un dataset individual:

```bash
datasets/scripts/convert/convert_datasets.py --datasets chv
```

## Salidas generadas

```text
datasets/processed/
  coco/
    original/
    canonical_cr01_cr02/
  yolo/
    original/
    canonical_cr01_cr02/
  odvg/
    original/
    canonical_cr01_cr02/
  reports/
```

## Vistas

### original

Conserva las clases originales de cada dataset. Es util para inspeccion, auditoria, entrenamiento cerrado por dataset o comparaciones con papers/fuentes originales.

### canonical_cr01_cr02

Normaliza clases a:

```text
person
helmet
vest
no_helmet
no_vest
```

Esta vista esta orientada a las condiciones iniciales del plan:

- CR-01: persona sin casco
- CR-02: persona sin chaleco reflectivo

## Formato COCO

Ruta:

```text
datasets/processed/coco/{view}/{dataset_id}/{split}.json
```

Convenciones:

- `bbox`: `[x, y, width, height]`
- `category_id`: entero contiguo desde 0
- `segmentation`: lista vacia
- `iscrowd`: 0

Ejemplo:

```text
datasets/processed/coco/canonical_cr01_cr02/chv/train.json
```

## Formato YOLO

Ruta:

```text
datasets/processed/yolo/{view}/{dataset_id}/
```

Convenciones:

- Labels generados en `labels/{split}/`.
- Listas de imagenes en `image_lists/{split}.txt`.
- `data.yaml` generado por vista/dataset.
- Las listas apuntan a las imagenes raw; no se duplican imagenes.

Ejemplo:

```text
datasets/processed/yolo/canonical_cr01_cr02/shel5k/data.yaml
```

## Formato ODVG

Ruta:

```text
datasets/processed/odvg/{view}/{dataset_id}/{split}.jsonl
```

Convenciones:

- Un objeto JSON por linea.
- `filename`: ruta de la imagen.
- `height` y `width`: dimensiones de la imagen.
- `detection.instances`: lista de instancias.
- Cada instancia contiene:
  - `bbox`: `[x1, y1, x2, y2]`
  - `label`: entero contiguo desde 0
  - `category`: nombre textual de clase

Cada directorio ODVG tambien incluye:

```text
label_map.json
```

Ejemplo:

```text
datasets/processed/odvg/canonical_cr01_cr02/sh17/train.jsonl
datasets/processed/odvg/canonical_cr01_cr02/sh17/label_map.json
```

## Splits

| Dataset | Politica |
|---|---|
| SH17 | Split oficial train/val |
| SHEL5K | Split custom 70/15/15 con seed 42 |
| CHV | Split oficial train/valid/test, normalizado como train/val/test |
| Construction-PPE | Split oficial train/val/test |

## Validacion realizada

Se valido que:

- Los JSON COCO parsean correctamente.
- Los JSONL ODVG parsean linea por linea.
- Las listas YOLO contienen la cantidad esperada de imagenes.
- Los conteos de anotaciones coinciden entre COCO, YOLO y ODVG por vista/dataset.
- `datasets/registry/datasets_metadata.yaml` parsea correctamente y marca los cuatro datasets prioritarios como `converted_coco_yolo_odvg`.

## Reportes

Reportes por dataset:

```text
datasets/processed/reports/chv_conversion_report.json
datasets/processed/reports/shel5k_conversion_report.json
datasets/processed/reports/construction_ppe_conversion_report.json
datasets/processed/reports/sh17_conversion_report.json
```

Resumen agregado:

```text
datasets/processed/reports/conversion_summary.json
```

Reporte legible:

```text
datasets/registry/conversion_report.md
```

