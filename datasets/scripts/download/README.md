# Scripts de descarga — v2

Scripts activos para los datasets seleccionados en el pipeline v2. Scripts de datasets v1 (SH17, SHEL5K, Construction-PPE) están en [`legacy/scripts/download/`](../../../legacy/scripts/download/).

## Datasets v2 activos

### construction_site_safety (TRAIN + BENCH)

```bash
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_construction_site_safety.sh
```

Descarga vía Roboflow API. Requiere `ROBOFLOW_API_KEY`.

### chv — Construction Hardhat Video (TRAIN + DEMO)

```bash
datasets/scripts/download/download_chv.sh
```

Descarga directa. Sin credenciales requeridas.

### ppe_siabar (TRAIN)

```bash
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_ppe_siabar.sh
```

Descarga vía Roboflow API. Requiere `ROBOFLOW_API_KEY`.

### construction_safety_hardhat (descartado — URL inválida)

```python
# datasets/scripts/download/download_construction_safety_hardhat.py
```

Script disponible pero el dataset no es accesible (URL de Kaggle inválida). Conservado como referencia.

## Después de descargar

Validar la descarga:

```bash
datasets/scripts/validate/summarize_raw_dataset.sh
```

Convertir a canonical_v2:

```bash
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety chv ppe_siabar \
    --views canonical_v2
```
