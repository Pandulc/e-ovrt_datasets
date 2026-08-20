# Scripts de descarga — v2

Scripts activos para los datasets seleccionados en el pipeline v2. Scripts de datasets v1 (SH17, Construction-PPE) están en [`legacy/scripts/download/`](../../../legacy/scripts/download/). El downloader de SHEL5K **volvió acá** el 2026-08-19 (estaba archivado en `legacy/` desde la era v1): SHEL5K es fuente canonical_v2 y estrato de bench_v3.

## Datasets v2 activos

### construction_site_safety

```bash
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_construction_site_safety.sh
```

Descarga vía Roboflow API. Requiere `ROBOFLOW_API_KEY`.

### chv — Color Helmet and Vest

```bash
datasets/scripts/download/download_chv.sh
```

Descarga directa. Sin credenciales requeridas. Requiere `unzip` para extraer.

### ppe_siabar

```bash
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_ppe_siabar.sh
```

Descarga vía Roboflow API. Requiere `ROBOFLOW_API_KEY`.

### shel5k

```bash
datasets/scripts/download/download_shel5k.sh
```

Descarga desde Mendeley Data (zip público con verificación sha256). Sin credenciales requeridas.

### construction_safety_hardhat (descartado — URL inválida)

```python
# legacy/scripts/download/download_construction_safety_hardhat.py
```

Script archivado en `legacy/` — el dataset no es accesible (URL de Kaggle inválida, nunca se descargó). Conservado como referencia.

## Después de descargar

Validar la descarga:

```bash
datasets/scripts/validate/summarize_raw_dataset.sh
```

Convertir a canonical_v2:

```bash
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety chv ppe_siabar shel5k \
    --views canonical_v2
```
