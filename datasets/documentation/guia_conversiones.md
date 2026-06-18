# Guía de conversiones COCO, YOLO y ODVG

Fecha de corte: 2026-06-18

## Script principal

```bash
# Convertir los 3 datasets activos a canonical_v2
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety ppe_siabar chv \
    --views canonical_v2

# También se puede convertir un dataset individual:
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets chv --views canonical_v2
```

## Salidas generadas

```text
datasets/processed/
  coco/
    canonical_v2/
      construction_site_safety/{train,val,test}.json
      ppe_siabar/{train,val,test}.json
      chv/{train,val,test}.json
    bench/
      construction_site_safety_bench.json   # val+test merged
      person_gt.json                        # GT persona-nivel (CR-01/CR-02)
  yolo/
    canonical_v2/
      construction_site_safety/
      ppe_siabar/
      chv/
  odvg/
    canonical_v2/
      construction_site_safety/
      ppe_siabar/
      chv/
```

## Vistas

### canonical_v2 (activa)

Vocabulario de detección canónico v2:

```text
person
helmet
vest
bare_head
```

`bare_head` solo se genera desde anotaciones negativas explícitas (e.g., `NO-Hardhat` en `construction_site_safety`). No se deriva por inferencia espacial (D9).

### original (histórica)

Conserva las clases originales de cada dataset. Útil para auditoría o comparación con papers.

### canonical_cr01_cr02 (DEPRECATED)

Vista v1 con clases `person, helmet, vest, no_helmet, no_vest`. Reemplazada por `canonical_v2`.  
Los scripts que la generan tienen `sys.exit()` guard — no ejecutar.

## Formato COCO

Ruta:

```text
datasets/processed/coco/{view}/{dataset_id}/{split}.json
```

Convenciones:

- `bbox`: `[x, y, width, height]`
- `category_id`: entero contiguo desde 0
- `segmentation`: lista vacía
- `iscrowd`: 0

Ejemplo:

```text
datasets/processed/coco/canonical_v2/construction_site_safety/train.json
```

## Formato YOLO

Ruta:

```text
datasets/processed/yolo/{view}/{dataset_id}/
```

Convenciones:

- Labels en `labels/{split}/`.
- Listas de imágenes en `image_lists/{split}.txt`.
- `data.yaml` generado por vista/dataset.
- Las listas apuntan a imágenes raw; no se duplican imágenes.

Ejemplo:

```text
datasets/processed/yolo/canonical_v2/chv/data.yaml
```

## Formato ODVG

Ruta:

```text
datasets/processed/odvg/{view}/{dataset_id}/{split}.jsonl
```

Convenciones:

- Un objeto JSON por línea.
- `filename`: ruta de la imagen.
- `height` y `width`: dimensiones.
- `detection.instances`: lista de instancias.
- Cada instancia: `bbox` en `[x1, y1, x2, y2]`, `label` (int), `category` (str).
- Directorio incluye `label_map.json`.

Ejemplo:

```text
datasets/processed/odvg/canonical_v2/construction_site_safety/train.jsonl
datasets/processed/odvg/canonical_v2/construction_site_safety/label_map.json
```

## Splits

| Dataset | Política |
|---|---|
| construction_site_safety | Split oficial Roboflow (train/val/test) |
| chv | Split oficial (train/val/test) |
| ppe_siabar | Split oficial Roboflow (train/val/test) |

## Validación

Se valida que:

- Los JSON COCO parsean correctamente.
- Los JSONL ODVG parsean línea por línea.
- Las listas YOLO tienen la cantidad esperada de imágenes.
- Los conteos coinciden entre COCO, YOLO y ODVG por vista/dataset.

## Registros de conversión

```text
datasets/registry/conversion_report.md    # resumen legible con conteos reales
```
