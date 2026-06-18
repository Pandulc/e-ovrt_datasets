# Protocolo Experimental de Detección de Ausencia de EPP

Fecha: 2026-06-18
Versión: 1.0
Proyecto: **E-OVRT-VDP** — repo `e-ovrt_datasets`
Estado: **congelado** — listo para implementar en `e-ovrt_media-plane`

---

## 0. Propósito y alcance

Este documento define el contrato de medición del experimento central de la tesis: comparar
tres enfoques para detectar la **ausencia de EPP** (casco, chaleco) en modelos de detección
de vocabulario abierto (OVD) — GroundingDINO, MM-GroundingDINO y YOLOE — sobre el banco de
evaluación BENCH.

Los valores numéricos marcados como **(confirmado)** fueron fijados como defaults en el diseño
v2 (§6 de `2026-06-17-reinicio-seleccion-datasets-design.md`) y **no se renegocian
individualmente** por resultado; solo se ajustan globalmente antes de ejecutar, con
justificación registrada.

Condiciones de riesgo evaluadas:
- **CR-01**: ausencia de casco de seguridad.
- **CR-02**: ausencia de chaleco reflectivo.

Modelos objetivo: GroundingDINO (GDINO), MM-GroundingDINO (MM-GDINO), YOLOE.

---

## 1. Métricas

### 1.1 Métrica primaria — nivel persona

Para cada condición (CR-01, CR-02) y cada celda de la matriz experimental:

| Métrica | Definición |
|---|---|
| **Precision** | TP / (TP + FP) — de las personas marcadas como violadoras, ¿cuántas lo son realmente? |
| **Recall** | TP / (TP + FN) — de las personas que sí son violadoras en el GT, ¿cuántas se detectan? |
| **F1** | Media armónica de Precision y Recall. |

La **unidad de medida es la persona**, no la caja de detección ni la imagen. Una persona
en el BENCH es un positivo (violadora) o un negativo (con EPP) según el GT a nivel persona
(`has_helmet`, `has_vest` por instancia de `person`).

### 1.2 Métrica secundaria — nivel detección (diagnóstico)

- **mAP@50** sobre las clases de detección (`person`, `helmet`, `vest`, `bare_head`) para
  diagnosticar la calidad de las detecciones base de cada modelo.
- Calculado en formato COCO estándar con umbral de IoU = 0.5 **(confirmado)**.
- No es la métrica de comparación principal entre E1/E2/E3; sirve para aislar si las fallas
  son de detección o de la lógica de decisión.

### 1.3 Umbral de IoU

**IoU = 0.5 (confirmado)** para todos los matchings detección↔persona y
detección↔región-de-cabeza descritos en §3.

---

## 2. Enfoques a comparar

| Enfoque | Descripción |
|---|---|
| **E1** | Positivos + lógica espacial: detectar `person`, `helmet`, `vest` y derivar la condición de riesgo por asociación espacial persona↔EPP. |
| **E2** | Objeto visual: detectar `bare_head` como clase positiva. Solo cubre CR-01. |
| **E3** | Negación por prompt: prompts de negación directos sobre el OVD. No requiere clase nueva; se evalúa contra el GT a nivel persona. |

Cada enfoque se evalúa en dos condiciones de fine-tuning:
- **sin-FT**: modelo en modo zero-shot (pesos base, sin fine-tuning en dominio de obra).
- **con-FT**: modelo con fine-tuning sobre el conjunto TRAIN del vocabulario canónico v2.

---

## 3. Matriz experimental — 6 celdas medibles

La matriz completa es E1/E2/E3 × CR-01/CR-02. `bare_head` no tiene equivalente para chaleco,
por lo que la celda E2×CR-02 es N/A por diseño (ver §7). Las 6 celdas medibles son:

| Enfoque | CR-01 (sin casco) | CR-02 (sin chaleco) |
|---|---|---|
| **E1** positivos + lógica | §3.1 | §3.2 |
| **E2** objeto visual (`bare_head`) | §3.3 | N/A — ver §7 |
| **E3** negación por prompt | §3.4 | §3.5 |

### 3.1 E1 × CR-01 — Positivos + lógica espacial (sin casco)

**Salida de detección usada:** cajas de clase `helmet` y cajas de clase `person`.

**Región de cabeza:** para cada detección `person` con caja `[x1, y1, x2, y2]`, la
*head_region* se define como el tercio superior:

```
head_region = [x1, y1, x2, y1 + (y2 - y1) / 3]
```

Esta geometría es la implementada en `geometry.head_region` del pipeline `e-ovrt_media-plane`.

**Regla de decisión a nivel persona:**

> Una persona es marcada como **violadora CR-01** (sin casco) si **ninguna** detección
> de clase `helmet` tiene su centro geométrico contenido dentro de la `head_region` de
> esa persona.

Formalmente: sea `(cx, cy)` el centro de una caja `helmet`. La persona `p` tiene casco
asociado si existe alguna caja `helmet` tal que `x1_p ≤ cx ≤ x2_p` y
`y1_p ≤ cy ≤ y1_p + (y2_p - y1_p) / 3`. Si no existe ninguna, la persona es marcada
violadora.

**GT contra el que se compara:** atributo `has_helmet` por instancia de persona en el BENCH.
`has_helmet = False` → persona violadora; `has_helmet = True` → persona conforme.

**Cómo se obtiene el número:** para cada imagen del BENCH se hace matching
detección-persona por IoU ≥ 0.5 entre las cajas `person` detectadas y las cajas `person`
del GT. Luego se aplica la regla anterior y se compara la clasificación resultante con el
atributo `has_helmet` del GT. Se acumulan TP/FP/FN sobre el conjunto completo del BENCH
y se calculan P/R/F1.

### 3.2 E1 × CR-02 — Positivos + lógica espacial (sin chaleco)

**Salida de detección usada:** cajas de clase `vest` y cajas de clase `person`.

**Región del torso:** para cada detección `person` con caja `[x1, y1, x2, y2]`, la
*vest_region* se define como los dos tercios inferiores (zona del torso donde se porta el
chaleco):

```
vest_region = [x1, y1 + (y2 - y1) / 3, x2, y2]
```

**Regla de decisión a nivel persona:**

> Una persona es marcada como **violadora CR-02** (sin chaleco) si **ninguna** detección
> de clase `vest` tiene su centro geométrico contenido dentro de la `vest_region` de
> esa persona.

**GT contra el que se compara:** atributo `has_vest` por instancia de persona en el BENCH.
`has_vest = False` → persona violadora; `has_vest = True` → persona conforme.

**Cómo se obtiene el número:** mismo procedimiento que §3.1, usando `vest` en lugar de
`helmet` y `vest_region` en lugar de `head_region`. Métrica: P/R/F1 a nivel persona sobre
violadoras CR-02.

### 3.3 E2 × CR-01 — Objeto visual `bare_head` (sin casco)

**Salida de detección usada:** cajas de clase `bare_head`.

**Regla de decisión a nivel persona:**

> Una persona es marcada como **violadora CR-01** si existe al menos una detección de clase
> `bare_head` cuya caja se solapa con la `head_region` de esa persona con **IoU ≥ 0.5
> (confirmado)** entre la caja `bare_head` y la `head_region`.

El solapamiento se calcula entre la caja detectada `bare_head` y la región geométrica
`head_region` de la persona del GT.

**GT contra el que se compara:** atributo `has_helmet` por instancia de persona en el BENCH
(mismo GT que E1×CR-01). `has_helmet = False` → persona violadora.

**Cómo se obtiene el número:** para cada persona en el GT del BENCH se computa si alguna
detección `bare_head` cumple el solapamiento con su `head_region`. La clasificación
resultante se compara con `has_helmet`. Se acumulan TP/FP/FN y se calculan P/R/F1.

**Nota de procedencia:** las detecciones `bare_head` en modo zero-shot usan los sinónimos
del §5. En modo con-FT, el modelo habrá sido entrenado con la clase `bare_head` obtenida
exclusivamente de negativos explícitos (cajas `NO-Hardhat` del dataset fuente), nunca
derivada por resta `head − helmet` (decisión D9).

### 3.4 E3 × CR-01 — Negación por prompt (sin casco)

**Salida de detección usada:** cajas devueltas por el modelo al recibir el prompt de
negación correspondiente a CR-01 (ver §4.1).

**Regla de decisión a nivel persona:**

> Una persona es marcada como **violadora CR-01** si existe al menos una detección del
> prompt de negación CR-01 cuya caja se solapa con la caja `person` del GT con
> **IoU ≥ 0.5 (confirmado)**.

El solapamiento se calcula directamente entre la caja del prompt de negación y la caja
`person` del GT (no se usa `head_region` aquí, porque el prompt describe a toda la
persona).

**GT contra el que se compara:** atributo `has_helmet` por instancia de persona en el BENCH.

**Cómo se obtiene el número:** mismo protocolo de acumulación de TP/FP/FN que los enfoques
anteriores. El prompt de negación se pasa una vez por imagen (para GDINO/MM-GDINO como
frase de phrase-grounding; para YOLOE como prompt de texto o visual, según §4.3). Las
cajas resultantes son las "detecciones de violadora" y se comparan contra el GT a nivel
persona.

### 3.5 E3 × CR-02 — Negación por prompt (sin chaleco)

**Salida de detección usada:** cajas devueltas por el modelo al recibir el prompt de
negación correspondiente a CR-02 (ver §4.2).

**Regla de decisión a nivel persona:**

> Una persona es marcada como **violadora CR-02** si existe al menos una detección del
> prompt de negación CR-02 cuya caja se solapa con la caja `person` del GT con
> **IoU ≥ 0.5 (confirmado)**.

**GT contra el que se compara:** atributo `has_vest` por instancia de persona en el BENCH.

**Cómo se obtiene el número:** mismo protocolo de acumulación de TP/FP/FN. Importante: la
clase `no_vest` **no fue entrenada** en ningún fine-tuning (decisión D6). Este enfoque
evalúa la capacidad open-vocabulary pura del modelo para responder a un prompt de ausencia
no visto durante el entrenamiento. Esa capacidad (o ausencia de ella) es parte del resultado
experimental.

---

## 4. Set de prompts congelado

Los prompts se **fijan antes de ejecutar cualquier experimento** y no se ajustan a
posteriori en función de los resultados (ver §6 del diseño v2 y decisión D12). El conjunto
a continuación constituye la versión 1.0 del set congelado.

### 4.1 E3 — Prompts de negación CR-01 (sin casco)

Aplicables a GDINO y MM-GDINO (phrase grounding):

| ID | Prompt |
|---|---|
| E3-CR01-P01 | `a person not wearing a safety helmet` |
| E3-CR01-P02 | `a worker without a hard hat` |
| E3-CR01-P03 | `a construction worker with no helmet` |
| E3-CR01-P04 | `a worker with bare head on a construction site` |

Aplicable a YOLOE (texto):

| ID | Prompt |
|---|---|
| E3-CR01-Y01 | `a person not wearing a safety helmet` |
| E3-CR01-Y02 | `a worker without a hard hat` |

### 4.2 E3 — Prompts de negación CR-02 (sin chaleco)

Aplicables a GDINO y MM-GDINO (phrase grounding):

| ID | Prompt |
|---|---|
| E3-CR02-P01 | `a person without a reflective vest` |
| E3-CR02-P02 | `a worker not wearing a safety vest` |
| E3-CR02-P03 | `a construction worker with no high-visibility vest` |
| E3-CR02-P04 | `a worker not wearing a reflective safety jacket` |

Aplicable a YOLOE (texto):

| ID | Prompt |
|---|---|
| E3-CR02-Y01 | `a person without a reflective vest` |
| E3-CR02-Y02 | `a worker not wearing a safety vest` |

### 4.3 Nota sobre YOLOE

YOLOE admite prompts de texto **y** prompts visuales (image crops como referencia). En
los experimentos zero-shot se usan prompts de texto listados arriba. En los experimentos
con-FT se usa el vocabulario aprendido de las clases de detección. Los prompts de texto
para YOLOE son idénticos a los de GDINO para que la comparación sea limpia (salvo que se
documente explícitamente una variante).

---

## 5. Mapeo de sinónimos zero-shot

Para E1 y E2, las clases canónicas (`helmet`, `vest`, `bare_head`, `person`) se
enuncian al modelo como frases en lenguaje natural. El mapeo es una variable experimental:
se fija y versiona aquí, y se usa **idéntico** en modo zero-shot y modo con-FT.

| Clase canónica | Sinónimos (todos se prueban en zero-shot; se selecciona el mejor por validación previa al BENCH) |
|---|---|
| `person` | `"person"`, `"worker"`, `"construction worker"`, `"laborer"` |
| `helmet` | `"safety helmet"`, `"hard hat"`, `"hardhat"`, `"construction helmet"` |
| `vest` | `"reflective vest"`, `"safety vest"`, `"high-visibility vest"`, `"hi-vis vest"`, `"reflective jacket"` |
| `bare_head` | `"bare head"`, `"uncovered head"`, `"head without helmet"`, `"worker without hard hat head"` |

**Procedimiento de selección del sinónimo:** antes de correr el BENCH, se evalúan los
sinónimos en un subconjunto de validación separado (no perteneciente al BENCH). El sinónimo
con mayor mAP@50 en esa validación se designa como "sinónimo principal" para los reportes.
Todos los sinónimos y sus mAP@50 individuales se reportan en el anexo de resultados.

---

## 6. Diseño de la comparación: zero-shot vs. fine-tuned

### 6.1 Regla de prompts fijos

Los prompts listados en §4 y el mapeo de sinónimos en §5 se **versionan en el repositorio
`e-ovrt_media-plane`** (en `configs/prompts/`) antes de ejecutar cualquier experimento.
Ningún resultado del BENCH se reporta con prompts ajustados a posteriori.

### 6.2 Comparación limpia

Para comparar zero-shot vs. fine-tuned:
- Se usan **los mismos prompts** en ambas condiciones.
- Se usa **el mismo BENCH** (mismo conjunto de imágenes y GT).
- La única variable que cambia es si el modelo recibió fine-tuning sobre el conjunto TRAIN.

Esta simetría garantiza que la diferencia observada en P/R/F1 se atribuye al fine-tuning y
no a diferencias en los prompts.

### 6.3 No hay ajuste post-hoc

Si un prompt produce resultados inesperadamente malos, se **documenta el resultado**; no se
reemplaza el prompt ni se excluye la corrida del reporte. El conjunto de prompts puede
revisarse en una versión posterior del protocolo, pero ese cambio implica re-ejecutar todo
el BENCH y reportar ambos sets.

---

## 7. Asimetría CR-02/E2 — resultado reportado

La celda **E2 × CR-02 es N/A** por diseño del vocabulario canónico v2:

- `bare_head` es visualmente detectable: una cabeza sin casco tiene apariencia distinta a
  una cabeza con casco.
- No existe una clase visual equivalente para "torso sin chaleco" (`no_vest`). La ausencia
  de chaleco no se puede reducir a un único patrón visual tan compacto como `bare_head`.
- Por lo tanto, CR-02 solo es medible mediante **E1** (lógica espacial con `vest`) y **E3**
  (prompt de negación).

Esta asimetría es un **hallazgo metodológico a reportar** en la tesis, no un descuido. Se
formula así:

> "La ausencia de casco (CR-01) tiene tres enfoques de detección evaluables (E1, E2, E3),
> porque `bare_head` es una clase visual reconocible. La ausencia de chaleco (CR-02) solo
> dispone de dos enfoques (E1, E3), porque no existe un objeto visual equivalente a
> `bare_head` para el chaleco. La asimetría impide una comparación directa E2 entre CR-01
> y CR-02 y es documentada como limitación de diseño del vocabulario."

---

## 8. Tamaño mínimo del BENCH

Por condición (CR-01 y CR-02 por separado):

- **≥ 150 personas-violadoras** (positivos: `has_helmet = False` o `has_vest = False`).
- **≥ 150 personas-conformes** (negativos: `has_helmet = True` o `has_vest = True`).

Valores **(confirmados)** como defaults en el diseño v2 (§6.5).

Si el BENCH final no alcanza estos mínimos para CR-02 (condición más difícil de cubrir), se
documenta como limitación de poder estadístico en los resultados: los intervalos de
confianza sobre P/R/F1 serán más amplios y las comparaciones menos concluyentes.

---

## 9. Resumen de la matriz — método de medición por celda

Tabla completa de referencia rápida:

| Celda | Detección usada | Regla decisión→persona | GT comparado | F1 reporta |
|---|---|---|---|---|
| **E1 × CR-01** | Cajas `helmet` + `person` | Ningún `helmet`.center en `head_region` → violadora | `has_helmet` del BENCH | F1 personas-violadoras CR-01 |
| **E1 × CR-02** | Cajas `vest` + `person` | Ningún `vest`.center en `vest_region` → violadora | `has_vest` del BENCH | F1 personas-violadoras CR-02 |
| **E2 × CR-01** | Cajas `bare_head` | `bare_head` IoU ≥ 0.5 con `head_region` → violadora | `has_helmet` del BENCH | F1 personas-violadoras CR-01 |
| **E2 × CR-02** | — | **N/A** (no existe clase visual; ver §7) | — | — |
| **E3 × CR-01** | Cajas del prompt E3-CR01 | Prompt-box IoU ≥ 0.5 con person-box → violadora | `has_helmet` del BENCH | F1 personas-violadoras CR-01 |
| **E3 × CR-02** | Cajas del prompt E3-CR02 | Prompt-box IoU ≥ 0.5 con person-box → violadora | `has_vest` del BENCH | F1 personas-violadoras CR-02 |

---

## 10. Artefactos y referencias cruzadas

| Artefacto | Ubicación | Contenido |
|---|---|---|
| Prompts versionados | `e-ovrt_media-plane/configs/prompts/` | YAML con set §4 por modelo |
| Sinónimos versionados | `e-ovrt_media-plane/configs/prompts/synonyms.yaml` | Mapeo §5 |
| GT del BENCH | `datasets/processed/coco/bench/` | Anotaciones con `has_helmet`, `has_vest` por persona |
| Auditoría del GT | `datasets/registry/bench_gt_audit.md` | Muestra ≥10 %/≥200 imágenes |
| Contrato de anotación | `datasets/registry/annotation_contract_v2.yaml` | Definiciones §4 del diseño v2 |
| Scoring selección | `datasets/registry/selection_scoring.csv` | Rúbrica por dataset |
| `geometry.head_region` | `e-ovrt_media-plane/src/eovrt_media/geometry.py` | Implementación de `head_region` |

---

## 11. Decisiones del diseño v2 incorporadas

| Decisión | Descripción | Dónde impacta en este protocolo |
|---|---|---|
| D1 | Objetivo: TRAIN + BENCH + DEMO | §8 (tamaño BENCH) |
| D2 | Comparar E1/E2/E3 | §2, §3 |
| D6 | `no_vest` no se entrena; E3 sí lo prueba | §3.5, §7 |
| D7 | `bare_head` entrenable | §3.3 |
| D9 | `bare_head` solo desde negativos explícitos | §3.3 (nota de procedencia) |
| D10 | GT del BENCH desde anotaciones explícitas, no por asociación espacial | §3 (GT vs. que se compara) |
| D12 | Prompts y sinónimos congelados | §4, §5, §6 |
| D14 | Mínimos de poder estadístico | §8 |
