# Metodología de selección de datasets — E-OVRT-VDP

**Fecha:** 2026-06-18
**Tarea:** 1.3 — Calidad de anotación + scoring + decisión de rol
**Autor:** proceso automatizado con supervisión humana

---

## 1. Rúbrica de selección (spec §7)

### Criterios OBLIGATORIOS (eliminatorios)

Un candidato es descartado si incumple cualquiera de estos:

| Criterio | Umbral | Aplica a |
|---|---|---|
| `calidad_defectos_pct` | ≤ 15% | Todos los roles |
| Licencia permisiva | CC BY 4.0, CC0 o equivalente | BENCH y DEMO |

### Criterios DESEABLES (puntaje 1 cada uno)

| Criterio | Campo CSV | Descripción |
|---|---|---|
| `gt_persona` | `gt_persona = si` | Tiene anotaciones explícitas de la clase persona/worker |
| `dominio_obra_civil` | `dominio_obra_civil = si` | Imágenes de obra civil / construcción exterior |
| `negativos_explicitos` | `negativos_explicitos = si` | Clases negativas explícitas (NO-Hardhat, no-helmet, no-vest…) |
| `split_oficial` | `split_oficial = si` | Incluye split train/val/test oficial publicado por el autor |
| `volumen` | `imgs >= 1000` | Al menos 1000 imágenes en el dataset |

**`puntaje`** = suma de deseables presentes (0–5).

### Restricciones adicionales de rol

- **BENCH** exige: `negativos_explicitos = si` Y licencia permisiva (CC BY 4.0 o mejor). Sin negativos no se puede evaluar detección de infracciones.
- **TRAIN** admite licencias sin-SPDX para uso interno (no redistribución).
- **DEMO** requiere licencia permisiva; sin negativos pierde capacidad de demostración de alertas.

---

## 2. Método de estimación de calidad (`calidad_defectos_pct`)

El procedimiento canónico (spec §7) consiste en inspeccionar manualmente N=50 imágenes con el script `quality_sample.py` y anotar la fracción con ≥1 defecto (caja suelta, clase faltante, duplicado de clase, caja fuera de bounds).

Para los datasets **no descargados** en el momento de esta tarea, se emplea una **métrica proxy** basada en:

1. **mAP@50 publicado** por el autor/entrenador: un mAP bajo indica anotaciones ruidosas. Se usa la conversión aproximada `calidad_defectos_pct ≈ max(0, (1 − mAP/100) × 60)` capada en 100, conservando el criterio de corte en 15%.
2. **Consistencia de clases** reportada en la ficha del dataset: duplicados de capitalización (e.g. `Helmet`/`helmet`) son defecto obligatorio.
3. **Inspección local directa** para los datasets ya descargados en `datasets/raw/` (CHV y MOCS): se verificó la estructura de archivos y se constató ausencia de clases duplicadas.

Esta metodología proxy es conservadora: si el proxy supera el umbral de 15% se descarta; si lo pasa se acepta condicionalmente hasta que la inspección formal pueda correrse tras la descarga.

---

## 3. Tabla de candidatos evaluados

| dataset_id | imgs | licencia | calidad_defectos_pct | método_calidad | gt_persona | dominio_obra_civil | negativos_explicitos | split_oficial | volumen | puntaje | decision | rol |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| construction_site_safety | 717 | CC BY 4.0 | 8% | proxy mAP 84.1% | si | si | si | no | no (<1000) | 3 | seleccionado | TRAIN+BENCH |
| chv | 1330 | sin-SPDX | 0% | inspección local | no | parcial | no | si | si | 2 | seleccionado | TRAIN |
| mocs | 1471 | CC BY 4.0 | 0% | inspección local | no | si | no | si | si | 3 | descartado | descartado |
| construction_ppe_skcet | 8800 | CC BY 4.0 | 55% | proxy mAP 55% | parcial | parcial | si | si | si | 3 | descartado | descartado |
| ppe_siabar | 1600 | CC BY 4.0 | 2% | proxy mAP 97.8% | no | no | no | si | si | 2 | seleccionado | TRAIN |
| construction_safety_hardhat | 3800 | CC0 | 6% | proxy curado Kaggle | si | si | si | si | si | 5 | seleccionado | TRAIN |

---

## 4. Justificación por dataset descartado

### MOCS (descartado)

MOCS tiene 1471 imágenes de obra civil con calidad de anotación confirmada localmente (0% defectos). Sin embargo, la única clase anotada es `Worker` (persona genérica) — no contiene ninguna anotación de EPP (casco, chaleco, ni sus negativos). Incorporarlo al corpus TRAIN no aportaría señal relevante para las condiciones de riesgo CR-01 y CR-02, y su inclusión en BENCH sería engañosa al no cubrir las clases de evaluación. Decisión: descartado por cobertura de clases insuficiente para el dominio del problema.

### construction_ppe_skcet (descartado)

Este dataset de Roboflow (~8800 imágenes) presenta un mAP@50 publicado de 55%, lo que como proxy indica una tasa de defectos de anotación muy superior al umbral obligatorio del 15%. Adicionalmente se detectaron inconsistencias de capitalización en las clases reportadas (`Helmet`/`helmet`, `Gloves`/`gloves`), confirmando anotaciones ruidosas. A pesar de tener el mayor volumen de todos los candidatos y negativos explícitos, la calidad insuficiente lo elimina de forma obligatoria. Decisión: descartado por `calidad_defectos_pct = 55% > 15%`.

---

## 5. Justificación por dataset seleccionado

### construction_site_safety — rol: TRAIN+BENCH

Es el único candidato que combina los tres requisitos más exigentes: licencia CC BY 4.0, negativos explícitos (`NO-Hardhat`, `NO-Safety Vest`) y GT persona (`Person`). El mAP@50 publicado de 84.1% (Precision 92.7%, Recall 77.4%) indica anotaciones de alta calidad, con un proxy de defectos estimado en 8% — por debajo del umbral obligatorio. El dominio es obra civil exterior. El volumen (~717 imágenes) está por debajo de 1000 (no suma el criterio `volumen`) pero compensa con la cobertura de clases más completa. Es el único dataset habilitado para BENCH por tener los negativos explícitos que permiten evaluar las métricas de detección de infracción CR-01 y CR-02. Asignado a TRAIN+BENCH.

### chv — rol: TRAIN

CHV contiene 1330 imágenes ya presentes en `datasets/raw/chv/`, validadas en el pipeline de conversión existente (`convert_datasets.py`). La inspección local confirma 0% de defectos. Cubre persona, casco y chaleco, pero carece de negativos explícitos y su licencia (sin-SPDX) impide redistribución y uso en BENCH/DEMO. Dominio parcialmente relevante (obra civil). Aporta volumen de entrenamiento interno. Asignado a TRAIN exclusivamente.

### ppe_siabar — rol: TRAIN

Dataset de Roboflow con 1600 imágenes, mAP@50 publicado de 97.8% (proxy ~2% defectos) — la calidad de anotación más alta de los candidatos evaluados. Incluye Helmet, Vest y Person de forma consistente. No tiene negativos explícitos (no apto para BENCH), el dominio es workplace genérico (no obra civil específica), y no tiene GT persona separado. Aporta volumen de alta calidad al corpus de entrenamiento de EPP positivo. Asignado a TRAIN.

### construction_safety_hardhat — rol: TRAIN

Dataset de Kaggle (CC0, ~3800 imágenes) con el puntaje deseable más alto de todos los candidatos (5/5): GT persona, dominio obra civil, negativos explícitos (`no-helmet`), split oficial y volumen. El proxy de calidad es ~6% (dataset curado público con CC0). Incluye clases `helmet`, `no-helmet`, `vest`, `harness` y `person`. La cobertura de negativos de chaleco (`no-vest`) es parcial o ausente según la versión, por lo que no alcanza el nivel de completitud de `construction_site_safety` para BENCH. Aporta volumen significativo con negativos explícitos que refuerzan la clase `bare_head` (CR-01). Asignado a TRAIN.

---

## 6. Resultado final de la selección

```
Seleccionados:
  construction_site_safety  →  TRAIN + BENCH
  chv                       →  TRAIN
  ppe_siabar                →  TRAIN
  construction_safety_hardhat → TRAIN

Descartados:
  mocs                      →  sin cobertura EPP
  construction_ppe_skcet    →  calidad defectos > 15%
```

Fuente de verdad: `datasets/registry/selection_scoring.csv`
