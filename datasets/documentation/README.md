# Documentación — E-OVRT-VDP Datasets

Fecha de corte: 2026-06-18

Índice de la documentación activa del repositorio de datasets. Todo lo anterior al reinicio v2 (2026-06-17) está en [`legacy/documentation/`](../../legacy/documentation/).

---

## Estado y avance

| Archivo | Contenido |
|---|---|
| [`estado_avance.md`](estado_avance.md) | Estado actual por fase, por dataset y por sprint experimental. **Leer primero.** |
| [`guia_conversiones.md`](guia_conversiones.md) | Formatos generados (COCO, YOLO, ODVG), rutas de salida, comandos de conversión y criterios de uso. |
| [`estructura-repositorio.md`](estructura-repositorio.md) | Árbol completo del repositorio, rol de cada directorio y flujo de datos de extremo a extremo. |

## Diseño y metodología

| Archivo | Contenido |
|---|---|
| [`2026-06-17-reinicio-seleccion-datasets-design.md`](2026-06-17-reinicio-seleccion-datasets-design.md) | Especificación del vocabulario v2 (`person/helmet/vest/bare_head`), vistas (`canonical_v2`, `train_v2`, `bench_v2`, `demo_v2`), criterios de selección y contrato de anotación. **Documento de diseño base.** |
| [`2026-06-18-metodologia-seleccion.md`](2026-06-18-metodologia-seleccion.md) | Procedimiento operativo para armar TRAIN y BENCH según el diseño v2. |
| [`2026-06-18-protocolo-experimental-ausencia.md`](2026-06-18-protocolo-experimental-ausencia.md) | Criterios de medición para CR-01/CR-02 en experimentos: métricas, umbrales, matriz experimental. |

## Referencia de datasets

| Archivo | Contenido |
|---|---|
| [`datasets_reference.md`](datasets_reference.md) | Referencia técnica v2: estructura raw, splits, clases originales, mapeo canonical_v2 y particularidades de cada dataset seleccionado. |
| [`investigacion-roboflow-universe.md`](investigacion-roboflow-universe.md) | Investigación de candidatos en Roboflow Universe evaluados para v2: scoring, clases disponibles, licencias. |

## Registros técnicos (en `datasets/registry/`)

| Archivo | Contenido |
|---|---|
| [`registry/datasets_metadata.yaml`](../registry/datasets_metadata.yaml) | Metadata de cada dataset: versión, rol, estado, mapeo de clases. |
| [`registry/annotation_contract_v2.yaml`](../registry/annotation_contract_v2.yaml) | Contrato formal de anotación v2 (qué anotar, qué no, criterios por clase). |
| [`registry/class_mapping.yaml`](../registry/class_mapping.yaml) | Mapeo detallado de clases originales → canonical_v2 por dataset. |
| [`registry/conversion_report.md`](../registry/conversion_report.md) | Reporte de conversión: conteos por dataset/split/clase en canonical_v2. |
| [`registry/bench_gt_audit.md`](../registry/bench_gt_audit.md) | Auditoría del GT persona-nivel del BENCH (Task 4.3 pendiente). |
| [`registry/download_log.md`](../registry/download_log.md) | Log de descargas: fechas, fuentes, checksums. |
| [`registry/license_registry.md`](../registry/license_registry.md) | Registro de licencias por dataset. |
| [`registry/selection_scoring.csv`](../registry/selection_scoring.csv) | Scoring de selección de candidatos v2. |
