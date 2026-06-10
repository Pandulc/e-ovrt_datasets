# Realineamiento fine-tuning CR-01/CR-02

Fecha: 2026-06-10

## Cambio de criterio

Los datasets preparados en este repositorio se usaran unicamente para fine-tuning de modelos. Por lo tanto, la vista operativa para entrenamiento debe estar curada y contener solo imagenes con combinaciones canonicas utiles para el aprendizaje de EPP y condiciones asociadas.

La vista `canonical_cr01_cr02` queda como vista intermedia de normalizacion de clases. No debe usarse directamente como entrada principal de fine-tuning porque conserva imagenes y combinaciones que no aportan al criterio curado actual.

## Vista recomendada

La vista recomendada para fine-tuning es:

```text
finetuning_cr01_cr02
```

Criterio de inclusion: se conserva una imagen solo si su conjunto de clases canonicas coincide exactamente con una combinacion aprobada.

Combinaciones mantenidas:

```text
helmet
vest
helmet+vest
helmet+person
person+vest
helmet+person+vest
person+no_helmet
helmet+person+no_helmet
person+no_helmet+vest
helmet+person+no_helmet+vest
no_helmet+vest
```

Combinaciones excluidas relevantes:

```text
person
no_helmet
helmet+no_helmet
helmet+no_helmet+vest
```

## Artefactos generados

COCO:

```text
datasets/processed/coco/finetuning_cr01_cr02/
```

YOLO:

```text
datasets/processed/yolo/finetuning_cr01_cr02/
```

ODVG:

```text
datasets/processed/odvg/finetuning_cr01_cr02/
```

Manifest:

```text
datasets/splits/cr01_cr02/finetuning_manifest.csv
```

Resumen:

```text
datasets/processed/reports/finetuning_cr01_cr02_summary.json
```

Script reproducible:

```text
datasets/scripts/curate/generate_finetuning_cr01_cr02.py
```

## Conteos

| Split | Imagenes | Anotaciones |
|---|---:|---:|
| train | 10611 | 86586 |
| val | 2273 | 17946 |
| test | 943 | 11471 |
| total | 13827 | 116003 |

Conteo de clases:

| Clase | Anotaciones |
|---|---:|
| person | 33313 |
| helmet | 41202 |
| vest | 3925 |
| no_helmet | 37563 |
| no_vest | 0 |

Conteo por combinacion:

| Combinacion | Imagenes |
|---|---:|
| no_helmet+person | 6337 |
| helmet+no_helmet+person | 4148 |
| helmet+person+vest | 1616 |
| helmet+person | 1374 |
| helmet+no_helmet+person+vest | 133 |
| person+vest | 83 |
| helmet+vest | 62 |
| no_helmet+person+vest | 51 |
| helmet | 13 |
| vest | 8 |
| no_helmet+vest | 2 |

## Observaciones metodologicas

- `no_vest` no aparece en el nucleo actual; CR-02 requiere asociacion persona-chaleco o anotacion complementaria si se necesita entrenar ausencia explicita.
- CHV aporta ejemplos positivos de `person`, `helmet` y `vest`, pero no incumplimientos explicitos.
- SHEL5K y SH17 aportan `no_helmet`, aunque parte de esa semantica deriva de `head`/`face`; debe reportarse como normalizacion operativa.
- Construction-PPE aporta `no_helmet` explicito y ejemplos de `person`, `helmet`, `vest`.
- Se excluyen casos `person` solo porque no aportan al fine-tuning especifico de EPP.
- Se excluyen casos `no_helmet` solo y `helmet+no_helmet` sin `person` por semantica debil o ambigua respecto de la condicion persona-EPP.
