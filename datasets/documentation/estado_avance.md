# Estado de avance

Fecha de corte: 2026-06-05

## Avance por semana del plan

| Semana | Objetivo | Estado | Observaciones |
|---|---|---|---|
| Semana 1 | Descarga y registro | Completado para nucleo inicial | SH17, SHEL5K, CHV y Construction-PPE descargados y registrados. |
| Semana 2 | Conversion y validacion | Completado a nivel basico | COCO, YOLO y ODVG generados para los cuatro datasets prioritarios. |
| Semana 3 | Mapeo de clases y splits | Parcial avanzado | Mapeo canonico y manifest combinado CR-01/CR-02 generados; falta producir artefactos combinados de entrenamiento/evaluacion si se requieren. |
| Semana 4 | Baseline inicial | Pendiente | Falta ejecutar baseline zero-shot con Grounding DINO y registrar metricas. |

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

## Manifest combinado CR-01/CR-02

`datasets/splits/cr01_cr02/split_manifest.csv` fue generado con una fila por imagen, rutas normalizadas al workspace actual, hash SHA256 de imagen y condicion canonica derivada de las etiquetas YOLO canonicas. SH17 se mantiene solo en train/val por no tener split test explicito.

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
- Para CR-02 no hay `no_vest` robusto en el nucleo actual.

## Proximo hito recomendado

Ejecutar baseline zero-shot con Grounding DINO sobre el test congelado del manifest combinado CR-01/CR-02 y registrar metricas por dataset, split y condicion.

