# Documentacion del corpus E-OVRT-VDP

Fecha de corte: 2026-06-05

Este directorio centraliza la documentacion operativa de la etapa de obtencion, validacion y conversion de datasets para el prototipo E-OVRT-VDP.

## Documentos

- `plan_obtencion_preparacion_datasets_e_ovrt_vdp.md`: plan original de trabajo.
- `procedimientos_realizados.md`: registro narrativo de las acciones ejecutadas.
- `estado_avance.md`: grado de avance por dataset y por semana del plan.
- `guia_conversiones.md`: formatos generados, rutas de salida y criterios de uso para COCO, YOLO y ODVG.

## Registros tecnicos relacionados

- `datasets/registry/datasets_metadata.yaml`
- `datasets/registry/class_mapping.yaml`
- `datasets/registry/download_log.md`
- `datasets/registry/license_registry.md`
- `datasets/registry/conversion_report.md`
- `datasets/processed/reports/conversion_summary.json`

## Estado resumido

Los cuatro datasets prioritarios de la etapa inicial ya estan descargados, validados a nivel basico y convertidos a COCO, YOLO y ODVG:

- SH17
- SHEL5K
- CHV
- Construction-PPE

Se generaron dos vistas por dataset:

- `original`: conserva clases originales.
- `canonical_cr01_cr02`: normaliza clases utiles para CR-01 y CR-02.

El manifest combinado CR-01/CR-02 ya fue generado en `datasets/splits/cr01_cr02/split_manifest.csv` con 15845 imagenes: 12175 en `train`, 2646 en `val` y 1024 en `test`. SH17 se mantiene solo en `train`/`val` porque no posee split `test` explicito.

