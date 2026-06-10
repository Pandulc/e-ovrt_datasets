# Procedimientos realizados

Fecha de corte: 2026-06-05

## 1. Estructura inicial

Se creo la estructura local definida por el plan:

```text
datasets/
  raw/
  processed/
    coco/
    yolo/
    odvg/
    reports/
  splits/
    cr01_cr02/
  registry/
  scripts/
    download/
    convert/
    validate/
    split/
  documentation/
```

Tambien se crearon los registros iniciales:

- `datasets/registry/datasets_metadata.yaml`
- `datasets/registry/class_mapping.yaml`
- `datasets/registry/license_registry.md`
- `datasets/registry/download_log.md`
- `datasets/splits/cr01_cr02/split_manifest.csv`

## 2. Descarga y registro de datasets prioritarios

### Construction-PPE

Se descargo desde la URL directa de Ultralytics:

```text
datasets/raw/construction_ppe/construction-ppe.zip
```

Resultado:

- Formato original: YOLO
- Imagenes: 1416
- Labels TXT: 1426
- Split oficial: train/val/test = 1132/143/141
- Licencia local verificada: AGPL-3.0
- SHA256: `bef8dcb599aa4e9d9f5e602cb6fa7143d3c84d7f6a0ff40463d7f2a4c2632ccc`

### CHV

Se descargo desde Google Drive oficial:

```text
datasets/raw/chv/CHV_dataset.zip
```

Resultado:

- Formato original: YOLO
- Imagenes: 1330
- Labels TXT: 1330
- Split oficial: train/valid/test = 1064/133/133
- SHA256: `e2a2ebef7b9a69fd2d7f5152eb808b14a3a0a76de015c802f3f187c437a8e577`

Clases confirmadas por README de anotaciones:

- `person`
- `vest`
- `blue helmet`
- `red helmet`
- `white helmet`
- `yellow helmet`

### SHEL5K

La descarga automatica desde Mendeley no fue posible por endpoints no expuestos o autorizacion. Luego se incorporo manualmente:

```text
datasets/raw/shel5k/9rcv8mm682-4.zip
```

Resultado:

- Formato original: Pascal VOC
- Imagenes: 5000
- XML: 5000
- Objetos: 75578
- Split oficial: no encontrado
- Licencia indicada por Mendeley: CC BY 4.0
- DOI: `10.17632/9rcv8mm682.4`
- SHA256: `dfba1d3ce01af69d791020cdfdfdbc25904b41724d11160361e7a4cd164e7a7a`

Validacion basica:

- Imagenes faltantes: 0
- XML corruptos: 0
- Boxes invalidas: 0
- Imagenes corruptas detectadas: 0

### SH17

Primero se descargo el repositorio oficial para conservar scripts, YAML y lista de URLs. Despues se configuro Kaggle con:

```text
/home/pandulc/.kaggle/kaggle.json
```

El archivo se dejo con permisos `600`.

Se descargo el dataset completo desde Kaggle:

```text
datasets/raw/sh17/sh17-kaggle.zip
```

Resultado:

- Formato original: YOLO + Pascal VOC
- Imagenes: 8099
- Labels YOLO: 8099
- XML VOC: 8099
- Metadata JSON: 8099
- Objetos: 75994
- Split oficial: train/val = 6479/1620
- Licencia indicada por fuente: CC BY-NC-SA 4.0
- SHA256: `4747f51cac891a59a55c354a7b0f3c3addb4478ab214e74c16f26a6a205abf73`

Validacion basica:

- Pairs imagen/YOLO/VOC/metadata completos: 8099/8099/8099/8099
- Lineas YOLO invalidas: 0
- Imagenes corruptas detectadas: 0
- Boxes VOC fuera de rango: 2

Decision: usar YOLO como fuente primaria para conversiones de SH17, porque los labels YOLO validaron sin cajas fuera de rango.

## 3. Scripts creados

Descarga:

- `datasets/scripts/download/download_construction_ppe.sh`
- `datasets/scripts/download/download_chv.sh`
- `datasets/scripts/download/download_sh17_repo.sh`
- `datasets/scripts/download/download_sh17_kaggle.py`

Validacion:

- `datasets/scripts/validate/summarize_raw_dataset.sh`

Conversion:

- `datasets/scripts/convert/convert_datasets.py`

## 4. Conversiones realizadas

Se generaron salidas en tres formatos:

- COCO
- YOLO
- ODVG para Grounding DINO

Tambien se generaron dos vistas:

- `original`
- `canonical_cr01_cr02`

Reporte detallado:

```text
datasets/registry/conversion_report.md
datasets/processed/reports/conversion_summary.json
```

## 5. Correccion de inconsistencias de registry

Se alinearon los registros tecnicos con el comportamiento real del conversor:

- `datasets/registry/class_mapping.yaml` ahora refleja que SH17 mapea `head` y `face` a `no_helmet` en la vista canonica.
- `datasets/registry/class_mapping.yaml` ahora usa los nombres reales de SHEL5K (`person_with_helmet`, `person_no_helmet`, `head_with_helmet`) en lugar de alias con espacios.
- Se agregaron notas metodologicas para distinguir `no_helmet` explicito de `no_helmet` inferido o normalizado.
- `datasets/registry/datasets_metadata.yaml` marca Construction-PPE como `downloaded_basic_validated`, consistente con las conversiones y validaciones ya registradas.
- El plan de obtencion fue ajustado para describir el mapeo operativo actual y no un mapeo preliminar desactualizado.

## 6. Manifest combinado CR-01/CR-02

Se genero el manifest combinado trazable:

```text
datasets/splits/cr01_cr02/split_manifest.csv
```

Criterios aplicados:

- Una fila por imagen.
- Rutas normalizadas al workspace actual bajo `datasets/raw/...`.
- Hash SHA256 por imagen.
- Condicion canonica derivada de las etiquetas YOLO canonicas.
- CHV, SHEL5K y Construction-PPE conservan `train`, `val` y `test`.
- SH17 se mantiene solo como `train` y `val` porque no posee split `test` explicito.

La vista `canonical_cr01_cr02` no debe interpretarse como un filtrado a imagenes con incumplimiento. Es una vista de normalizacion de clases. Para organizar mejor su uso experimental se agregaron manifests derivados generados por:

```text
datasets/scripts/split/generate_cr01_cr02_views.py
```

Artefactos generados:

```text
datasets/splits/cr01_cr02/view_manifest.csv
datasets/splits/cr01_cr02/condition_positive_manifest.csv
datasets/splits/cr01_cr02/canonical_positive_context_manifest.csv
datasets/splits/cr01_cr02/no_canonical_annotations_manifest.csv
datasets/splits/cr01_cr02/view_summary.json
```

Definiciones:

- `condition_positive`: imagen con al menos una anotacion canonica `no_helmet` o `no_vest`.
- `canonical_positive_context`: imagen sin `no_helmet/no_vest`, pero con `person`, `helmet` o `vest`.
- `no_canonical_annotations`: imagen que queda sin anotaciones luego del remapeo canonico.

Conteo final por split:

| Split | Imagenes |
|---|---:|
| train | 12175 |
| val | 2646 |
| test | 1024 |

Detalle por dataset:

| Dataset | train | val | test |
|---|---:|---:|---:|
| CHV | 1064 | 133 | 133 |
| SHEL5K | 3500 | 750 | 750 |
| Construction-PPE | 1132 | 143 | 141 |
| SH17 | 6479 | 1620 | 0 |

Validaciones realizadas sobre el manifest:

- Total de filas: 15845.
- Duplicados por `source_image`: 0.
- Duplicados por `hash_sha256`: 0.
- Solapamientos entre splits por ruta o hash: 0.

Decision metodologica: `val` queda destinado a calibracion de prompts, umbrales y postproceso; `test` queda congelado para la baseline DBE zero-shot y cualquier comparacion posterior.

