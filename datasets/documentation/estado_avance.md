# Estado de avance

Fecha de corte: 2026-06-05

## Avance por semana del plan

| Semana | Objetivo | Estado | Observaciones |
|---|---|---|---|
| Semana 1 | Descarga y registro | Completado para nucleo inicial | SH17, SHEL5K, CHV y Construction-PPE descargados y registrados. |
| Semana 2 | Conversion y validacion | Completado a nivel basico | COCO, YOLO y ODVG generados para los cuatro datasets prioritarios. |
| Semana 3 | Mapeo de clases y splits | Parcial avanzado | Mapeo canonico y manifest combinado CR-01/CR-02 generados; falta producir artefactos combinados de entrenamiento/evaluacion si se requieren. |
| Semana 4 | Baseline inicial | Pendiente | Falta ejecutar baseline zero-shot con Grounding DINO y registrar metricas. |

Actualizacion 2026-06-10: se realineo el criterio de uso de datasets. Los datasets quedan orientados exclusivamente a fine-tuning y la vista recomendada pasa a ser `finetuning_cr01_cr02`, curada por combinaciones canonicas aprobadas para fine-tuning.

## Avance por dataset prioritario

| Dataset | Descarga | Validacion basica | COCO | YOLO | ODVG | Split |
|---|---|---|---|---|---|---|
| SH17 | Completa | Completa con observacion VOC | Generado | Generado | Generado | Oficial train/val, sin test explicito |
| SHEL5K | Completa | Completa | Generado | Generado | Generado | Custom 70/15/15 seed 42 |
| CHV | Completa | Completa | Generado | Generado | Generado | Oficial train/val/test |
| Construction-PPE | Completa | Completa | Generado | Generado | Generado | Oficial train/val/test |

## Conteos convertidos

| Dataset | Vista | Imagenes | Anotaciones |
|---|---|---:|---:|
| CHV | original | 1330 | 9209 |
| CHV | canonical_cr01_cr02 | 1330 | 9209 |
| SHEL5K | original | 5000 | 75578 |
| SHEL5K | canonical_cr01_cr02 | 5000 | 75578 |
| Construction-PPE | original | 1416 | 11521 |
| Construction-PPE | canonical_cr01_cr02 | 1416 | 6082 |
| SH17 | original | 8099 | 75994 |
| SH17 | canonical_cr01_cr02 | 8099 | 36194 |

Vista curada para fine-tuning:

| Vista | Imagenes | Anotaciones |
|---|---:|---:|
| finetuning_cr01_cr02 | 13827 | 116003 |

## Manifest combinado CR-01/CR-02

`datasets/splits/cr01_cr02/split_manifest.csv` fue generado con una fila por imagen, rutas normalizadas al workspace actual, hash SHA256 de imagen y condicion canonica derivada de las etiquetas YOLO canonicas. SH17 se mantiene solo en train/val por no tener split test explicito.

La vista `canonical_cr01_cr02` normaliza clases al espacio `person`, `helmet`, `vest`, `no_helmet`, `no_vest`, pero no filtra imagenes por condicion positiva. Por lo tanto, puede contener imagenes con clases canonicas de contexto o imagenes que quedan sin anotaciones canonicas luego del remapeo.

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

## Condiciones cubiertas

### CR-01 - Persona sin casco

Cobertura actual:

- SH17: contiene `person`, `helmet`, `head`, `face`.
- SHEL5K: contiene `helmet`, `head_with_helmet`, `person_with_helmet`, `head`, `person_no_helmet`, `face`.
- CHV: contiene `person` y cascos por color, pero no etiqueta explicita de no casco.
- Construction-PPE: contiene `Person`, `helmet`, `no_helmet`.

Estado: cobertura fuerte para evaluacion inicial.

### CR-02 - Persona sin chaleco reflectivo

Cobertura actual:

- SH17: contiene `safety-vest`, pero no etiqueta explicita `no_vest`.
- CHV: contiene `person` y `vest`, pero no etiqueta explicita `no_vest`.
- Construction-PPE: contiene `vest`, pero no etiqueta explicita `no_vest` en el YAML descargado.
- SHEL5K: no cubre chaleco.

Estado: cobertura parcial. Para detectar incumplimiento de chaleco probablemente se requiera logica por asociacion persona-chaleco o anotacion complementaria.

## Riesgos y observaciones

- SH17 trae 2 cajas Pascal VOC fuera de rango; se documentaron y se evita el problema usando YOLO como fuente primaria.
- SHEL5K no trae split oficial; se genero split custom reproducible con seed 42.
- ODVG fue generado para entrenamiento/uso con Grounding DINO, pero falta validar con la configuracion exacta del framework que se vaya a ejecutar.
- La vista `canonical_cr01_cr02` reduce clases no relevantes, pero la interpretacion de `no_helmet` en algunos datasets deriva de `head`/`face`; esto debe documentarse en evaluaciones.
- Se generaron manifests derivados para separar imagenes con condicion positiva, contexto canonico positivo y casos sin anotaciones canonicas.
- Para CR-02 no hay `no_vest` robusto en el nucleo actual.

## Vistas derivadas CR-01/CR-02

Se generaron manifests derivados en `datasets/splits/cr01_cr02/` para organizar la distribucion sin duplicar ni mover imagenes:

- `view_manifest.csv`: manifest general con columna `view`.
- `condition_positive_manifest.csv`: imagenes con al menos una anotacion canonica `no_helmet` o `no_vest`.
- `canonical_positive_context_manifest.csv`: imagenes sin `no_helmet/no_vest`, pero con `person`, `helmet` o `vest`.
- `no_canonical_annotations_manifest.csv`: imagenes que quedan sin anotaciones canonicas luego del remapeo.
- `view_summary.json`: resumen de conteos por vista, split y dataset.

Conteo global:

| Vista derivada | Imagenes |
|---|---:|
| condition_positive | 11171 |
| canonical_positive_context | 4241 |
| no_canonical_annotations | 433 |

Conteo en `train`:

| Vista derivada | Imagenes |
|---|---:|
| condition_positive | 8498 |
| canonical_positive_context | 3337 |
| no_canonical_annotations | 340 |

## Proximo hito recomendado

Usar `finetuning_cr01_cr02` como entrada curada para los experimentos de fine-tuning y documentar metricas por dataset, split y clase canonica.

