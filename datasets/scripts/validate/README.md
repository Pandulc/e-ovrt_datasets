# Validation Scripts

Scripts iniciales para inspeccionar datasets crudos antes de conversion.

## Uso

```bash
datasets/scripts/validate/summarize_raw_dataset.sh construction_ppe
```

El resumen registra conteos de archivos, imagenes y posibles anotaciones. Despues de cada descarga, copiar los datos relevantes a `datasets/registry/download_log.md` y `datasets/registry/datasets_metadata.yaml`.
