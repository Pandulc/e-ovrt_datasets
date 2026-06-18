# Diseño — Reinicio de selección de datasets (v2)

Fecha: 2026-06-17 (rev. 2026-06-18: cubiertas brechas metodológicas G1–G9)
Proyecto: **E-OVRT-VDP** — repo `e-ovrt_datasets`
Estado: diseño aprobado (brainstorming), pendiente de plan de implementación.

---

## 0. Motivación

El corpus y procesamiento previos se construyeron **antes** de seleccionar bien los
datasets: se convirtieron, normalizaron y splitearon fuentes de calidad heterogénea, y
luego tres de los cuatro datasets de EPP (SH17, SHEL5K, Construction-PPE) terminaron
archivados por calidad. La vista `finetuning_cr01_cr02` quedó apoyada en anotaciones de
ausencia ruidosas (`no_helmet` derivado de `head`/`face`) o inexistentes (`no_vest` = 0
anotaciones).

Este documento define un **reinicio metodológico**: primero seleccionar con criterios
explícitos, después procesar. El objetivo es preparar el repositorio completo para tres
usos —fine-tuning, benchmark de evaluación y demo de tesis— y soportar un **experimento
comparativo sobre cómo detectar la ausencia de EPP en modelos OVD**.

Las condiciones de riesgo iniciales se mantienen: **CR-01** (sin casco) y **CR-02**
(sin chaleco). Los modelos OVD objetivo son **GroundingDINO, MM-GroundingDINO y YOLOE**.

> Esta revisión cubre las brechas detectadas en la revisión crítica del 2026-06-18:
> construcción del GT del BENCH y circularidad (G1), procedencia de `bare_head` (G2),
> protocolo de medición (G3), contrato de anotación (G4), fuga/OOD (G5), balance y poder
> estadístico (G6), rúbrica operable (G7), formatos por modelo (G8), privacidad (G9).

---

## 1. Entregables

El repo produce tres salidas, cada una con su propia vara de calidad:

| Salida | Propósito | Vara de calidad |
|---|---|---|
| **TRAIN** | fine-tuning de los OVD al dominio de obra | Calidad de anotación + licencia (obligatorios). Volumen y dominio (deseables). Contrato de anotación §4. |
| **BENCH** | evaluación confiable (zero-shot y post-FT) | Lo anterior **+ GT a nivel persona obligatorio** (`has_helmet`, `has_vest`) construido según §5. |
| **DEMO** | imágenes para la defensa de tesis | Obra civil real + alta calidad visual. Conjunto chico. Tratamiento de privacidad (§9, G9). |

---

## 2. Estrategia de detección de ausencia — los tres enfoques a comparar

Los OVD aterrizan frases de texto a regiones: detectan **presencia** de lo que el prompt
describe; la **negación** es su punto débil documentado. El experimento central de la
tesis compara tres formas de resolver CR-01/CR-02:

- **E1 — Positivos + lógica espacial**: detectar `person`/`helmet`/`vest` y **derivar** la
  condición de riesgo por asociación persona↔EPP (una persona sin casco asociado → CR-01).
  Robusto y alineado a cómo funcionan los detectores. La lógica de asociación vive en el
  pipeline (`e-ovrt_media-plane`), no en los datos.
- **E2 — Ausencia como objeto visual**: clase positiva `bare_head` (cabeza descubierta),
  que **sí** es visualmente detectable. Solo aplica a casco (CR-01).
- **E3 — Negación por prompt**: prompts de negación directos sobre el OVD
  (*"person not wearing a helmet"*, *"person without a reflective vest"*). No requiere
  anotación nueva; se evalúa contra el GT a nivel persona.

### 2.1 Separación clave: vocabulario de entrenamiento ≠ espacio de prompts de evaluación

Decisión explícita (a documentar como resultado metodológico):

- **`no_vest` NO se entrena** (ninguna fuente lo cubre con calidad). Tampoco `no_helmet`
  como tal.
- **Pero E3 sí prueba prompts de ausencia de chaleco**, aunque esa clase nunca se entrenó.
  Ese es justamente el experimento: medir si el OVD detecta —por capacidad
  open-vocabulary pura— una ausencia que **no** está en su vocabulario de fine-tuning.

### 2.2 Matriz experimental

| Enfoque | CR-01 (casco) | CR-02 (chaleco) | sin fine-tuning | con fine-tuning |
|---|---|---|---|---|
| **E1** positivos + lógica | ✅ | ✅ | ✅ | ✅ |
| **E2** objeto visual (`bare_head`) | ✅ | — (sin clase) | ✅ | ✅ |
| **E3** negación por prompt | ✅ | ✅ (vest **sin entrenar**) | ✅ | ✅ |

Para que la matriz sea medible, el **BENCH debe cargar GT a nivel persona de `has_helmet`
y `has_vest`** (§5). `has_vest` es lo único que habilita evaluar E3-vest, tanto sin como
con fine-tuning.

---

## 3. Vocabulario canónico v2

- **Clases de detección** (TRAIN + BENCH): `person`, `helmet`, `vest`, `bare_head`.
- **Atributos a nivel persona** (solo en el GT del BENCH): `has_helmet`, `has_vest`.
- **No modelado como clase de detección**: `no_vest` (ni `no_helmet` genérico). CR-02 se
  evalúa por el atributo `has_vest`; la ausencia de chaleco solo se "detecta" vía prompt
  E3.

Asimetría intencional: casco tiene enfoque visual propio (`bare_head`), chaleco no. Esa
asimetría es un hallazgo a reportar, no un descuido.

### 3.1 Procedencia de `bare_head` (G2 — no repetir el error viejo)

**Regla dura:** `bare_head` se obtiene **solo de etiquetas negativas explícitas** sobre la
cabeza (p. ej. `NO-Hardhat` anotado como caja de cabeza/persona descubierta). **Está
prohibido derivar `bare_head` por resta `head − helmet`** ni a partir de `head`/`face`
genéricos: esa derivación es la que volvió ruidoso el `no_helmet` anterior y queda
explícitamente vetada.

Consecuencia de diseño feliz: **las mismas cajas negativas explícitas sirven a la vez**
para (a) entrenar `bare_head` en E2 y (b) construir el GT `has_helmet` del BENCH (§5), sin
introducir circularidad. Esto convierte "tener negativos explícitos a nivel cabeza/persona"
en requisito de las fuentes destinadas a BENCH y a entrenar E2.

---

## 4. Contrato de anotación v2 (G4 — armonización entre fuentes)

Fusionar varias fuentes en un solo corpus introduce **ruido por anotación parcial**: si la
fuente A etiqueta `person` y la B no, las personas de B se vuelven negativos falsos que
envenenan el fine-tuning. El contrato define qué significa cada clase y cómo se concilian
fuentes heterogéneas.

### 4.1 Definición operativa de cada clase

| Clase | Qué encierra la caja | Notas |
|---|---|---|
| `person` | Cuerpo completo visible de la persona/trabajador | Incluye la cabeza. |
| `helmet` | El casco propiamente dicho (la prenda), no toda la cabeza | Caja ceñida al casco. |
| `vest` | El chaleco reflectivo/de seguridad (la prenda) | Caja ceñida al torso con chaleco. |
| `bare_head` | La **cabeza descubierta** de una persona sin casco | Solo desde negativo explícito (§3.1). Mutuamente excluyente con `helmet` sobre la misma cabeza. |

### 4.2 Reglas de conciliación

- **Exhaustividad por clase y por fuente**: para cada dataset se registra qué clases anota
  de forma **exhaustiva** (todas las instancias) vs. **parcial/ausente**. Una clase no
  anotada exhaustivamente en una fuente **no** se trata como negativo en esa fuente.
- **Fuentes con clases faltantes**: dos opciones permitidas, decididas por dataset en la
  selección (§7): (a) no incluir esa fuente en los splits donde la clase ausente importa,
  o (b) completar la clase ausente con una pasada de anotación. **No** se mezcla una fuente
  con clase faltante como si esa clase no existiera.
- **`helmet` vs `bare_head`**: excluyentes sobre la misma cabeza; una cabeza tiene casco o
  está descubierta, nunca ambas.
- El contrato se versiona como artefacto: `datasets/registry/annotation_contract_v2.yaml`
  (definiciones + matriz fuente×clase con exhaustiva/parcial/ausente).

---

## 5. Construcción del GT del BENCH y control de circularidad (G1)

El BENCH es el patrón de medición; la corrección de su GT importa más que la de ningún
otro artefacto.

### 5.1 Origen del GT a nivel persona

`has_helmet` y `has_vest` por persona se construyen **a partir de anotaciones explícitas a
nivel cabeza/persona** (cajas `NO-Hardhat` / `NO-Safety-Vest` que *son* la región de la
persona), **no** por asociación espacial de cajas independientes.

### 5.2 Por qué no se usa asociación espacial para construir el GT (anti-circularidad)

E1 decide la condición de riesgo asociando `person` con `helmet`/`vest` por solapamiento
espacial. **Si el GT del BENCH se construyera con esa misma asociación, E1 quedaría
evaluado contra un GT generado por su propio procedimiento** → ventaja artificial para E1
y castigo para E3. Por eso el GT del BENCH se ancla en anotaciones explícitas
independientes del método E1.

### 5.3 Auditoría del GT del BENCH

Antes de congelar el BENCH se audita manualmente una **muestra aleatoria** (objetivo:
≥10 % de imágenes o ≥200 imágenes, lo que sea menor) verificando que `has_helmet`/`has_vest`
por persona sean correctos. El resultado de la auditoría (tasa de error encontrada) se
registra en `datasets/registry/bench_gt_audit.md`.

---

## 6. Protocolo experimental de medición (G3)

Define cómo se puntúa cada celda de la matriz §2.2. Los valores numéricos son **defaults**
a confirmar antes de ejecutar.

### 6.1 Métrica

- Por condición (CR-01, CR-02) y a **nivel persona**: Precision / Recall / F1 sobre el
  conjunto de personas-violadoras (sin casco / sin chaleco).
- Secundario: mAP@50 de las clases de detección (`person`/`helmet`/`vest`/`bare_head`)
  para diagnosticar la calidad de detección base por modelo.

### 6.2 Regla detección → decisión a nivel persona

- Matching detección↔persona por IoU ≥ **0.5** (default) contra la caja persona del GT.
- **E1**: persona marcada "sin casco" si **no** hay detección `helmet` asociada a su región
  de cabeza (contención del centro de la caja `helmet` en el tercio superior de la persona).
  Análogo con `vest` para CR-02.
- **E2**: persona marcada "sin casco" si hay una detección `bare_head` solapando su región
  de cabeza.
- **E3**: persona marcada "violadora" si una detección del prompt de negación solapa su caja
  con IoU ≥ 0.5.

### 6.3 Set de prompts congelado (evitar cherry-picking)

El conjunto de prompts por enfoque/condición se **fija y versiona** en
`e-ovrt_media-plane` (configs de prompts) antes de correr, y se documenta en el protocolo.
Ningún resultado se reporta con prompts ajustados a posteriori. Como mínimo se congela:
1–2 frases de negación por condición para E3 (p. ej. *"a person without a safety helmet"*,
*"a worker not wearing a reflective vest"*) y el mapeo de sinónimos de §6.4.

### 6.4 Mapeo de sinónimos para zero-shot

Las clases canónicas necesitan equivalentes en lenguaje natural para el prompting
(`helmet` → "hard hat / safety helmet"; `vest` → "reflective safety vest"; etc.). Ese
mapeo es **una variable experimental**: se fija y versiona junto con el set de prompts, y
se usa idéntico en sin-FT y con-FT para que la comparación sea limpia.

### 6.5 Poder estadístico mínimo del BENCH (G6)

El BENCH debe contener, **por condición**, un mínimo de casos para que la métrica sea
significativa. Objetivo (default a confirmar): **≥150 personas-positivas y ≥150
personas-negativas por condición**. Si una fuente no alcanza el mínimo en CR-02
(ausencia de chaleco), se complementa o se documenta la limitación de potencia.

---

## 7. Rúbrica de selección de datasets (G7 — operable y reproducible)

**Criterios que descartan (obligatorios):**
1. **Calidad de anotación** verificable mediante **procedimiento concreto**: muestrear
   **N = 50** imágenes por dataset y revisarlas contra un checklist (cajas ajustadas, sin
   faltantes/duplicados, clases consistentes, sin solapes inconsistentes). Se descarta si
   la tasa de imágenes con defectos supera un umbral (default **>15 %**).
2. **Licencia permisiva** — CC BY 4.0 o más permisiva, redistribuible con atribución, al
   menos para lo que se publica/presenta (BENCH y DEMO). Evitar AGPL-en-datos y
   sin-SPDX para esos roles.

**Criterios que puntúan (deseables, no descartan):**
- GT a nivel persona / negativos explícitos (`NO-Hardhat`, `NO-Vest`).
- Dominio obra civil / exterior (vs. estudio o industria genérica).
- Volumen de imágenes y objetos (y aporte al balance de clases, §7.1).
- Split oficial reproducible.
- Realismo del EPP respecto del contexto objetivo.

**Excepciones de rol:**
- GT a nivel persona / negativos explícitos pasan de "deseable" a **obligatorio para BENCH**
  (y para entrenar E2, §3.1). TRAIN se rige solo por los dos obligatorios generales.

**Artefacto reproducible (G7):** el scoring de cada candidato se registra como datos en
`datasets/registry/selection_scoring.csv` (una fila por dataset, columnas = criterios +
puntaje + decisión + rol asignado), no solo en prosa. La selección debe ser auditable.

### 7.1 Balance de clases en TRAIN (G6)

Se fijan **mínimos por clase** en TRAIN para evitar el desbalance histórico (`vest` era
~10× menor que `helmet`). Si una clase (típicamente `vest`) queda por debajo del mínimo,
la selección debe priorizar fuentes que la aporten o aplicar estrategias de balanceo
(submuestreo de la clase dominante / sobremuestreo dirigido), documentadas.

---

## 8. Proceso (en el orden correcto)

La regla aprendida: **no procesar nada antes de seleccionar.**

1. **Survey sistemático** — relevar candidatos (Roboflow Universe, papers, Kaggle)
   aplicando la rúbrica de la §7 → `selection_scoring.csv`. Punto de partida ya
   identificado: el referente *Construction Site Safety* (Roboflow Universe Projects),
   que tiene `Hardhat`/`NO-Hardhat`/`Safety Vest`/`NO-Safety Vest`/`Person` explícitos
   (cubre G1, G2 y BENCH a la vez).
2. **Selección + asignación de rol** — con revisión humana, asignar cada dataset elegido a
   TRAIN / BENCH / DEMO, registrando exhaustividad por clase (§4.2).
3. **Descarga + verificación** — hash SHA256, conteos, muestreo visual de anotaciones
   (checklist de §7.1).
4. **Conversión a vocabulario v2** — reusando `convert_datasets.py`; actualizar `configs()`
   con mapeos v2 (`person`/`helmet`/`vest`/`bare_head`), la extracción de atributos
   persona-nivel para el BENCH (§5) y el contrato de anotación (§4).
5. **Curación + splits** — **solo** sobre lo seleccionado. Control de **fuga TRAIN↔BENCH**
   (G5): separación por escena/fuente; el BENCH debe ser **held-out** respecto de TRAIN
   (idealmente una fuente distinta, o como mínimo sin imágenes/escenas compartidas).
   Aplicar mínimos de balance (§7.1) y de poder estadístico (§6.5).
6. **Registry** — reescribir provenance, licencias y mapeos v2. Artefactos nuevos:
   `annotation_contract_v2.yaml`, `selection_scoring.csv`, `bench_gt_audit.md`.

### 8.1 Formatos de export por modelo (G8)

| Formato | Consume | Notas |
|---|---|---|
| **ODVG** | GroundingDINO, MM-GroundingDINO | Phrase grounding; los prompts de negación de E3 se inyectan en evaluación, no se entrenan. |
| **YOLO** | YOLOE | YOLOE admite prompts de texto **y visuales**; GDINO/MM-GDINO no. Tenerlo en cuenta al diseñar E3 por modelo. |
| **COCO** | intercambio / métricas | Formato pivote para evaluación y auditoría. |

---

## 9. Tratamiento de lo existente y privacidad

- **Scripts** (`convert/`, `validate/`, `split/`, `curate/`) → se conservan y se adaptan a
  v2. Lo que falló fue el orden de uso, no el código.
- **Vistas procesadas y splits actuales** (`canonical_cr01_cr02`, `finetuning_cr01_cr02`,
  `splits/cr01_cr02/`) → se marcan **DEPRECATED** y se regeneran tras la nueva selección.
  **No se borran** hasta tener reemplazo validado.
- **Datasets archivados** (`raw/archived/`) → permanecen archivados; pueden re-evaluarse
  bajo la rúbrica v2 si algún rol lo justifica.
- **Registry** → se reescribe para v2; la versión previa queda en git history.
- **Privacidad en DEMO (G9)** → las imágenes con rostros visibles que se muestren en la
  defensa pública se evalúan según licencia/jurisdicción; aplicar blurring de rostros por
  defecto en el set DEMO salvo que la licencia/consentimiento lo permita explícitamente.

---

## 10. Documentación de tesis (sub-entregables)

- **Metodología de selección**: rúbrica + `selection_scoring.csv` + justificación de cada
  decisión de inclusión/exclusión y de asignación de rol.
- **Protocolo experimental de ausencia**: §6 expandida — definición operativa de E1/E2/E3,
  métricas, regla detección→persona, set de prompts y sinónimos congelados, y diseño de la
  comparación sin-FT vs con-FT.
- **Contrato de anotación v2** y **auditoría del GT del BENCH**.

---

## 11. Fuera de alcance

- La **lógica de asociación persona↔EPP** (E1) y la ejecución de los prompts (E3) viven en
  `e-ovrt_media-plane`. Aquí solo se produce el dato + el GT que las habilita; §6 define el
  contrato de medición que ambos repos deben respetar.
- El **fine-tuning** de los modelos en sí (consumidor del entregable TRAIN).
- Condiciones de riesgo más allá de CR-01/CR-02 (maquinaria, vehículos, etc.).

---

## 12. Decisiones registradas

| # | Decisión | Estado |
|---|---|---|
| D1 | Objetivo: preparar el repo completo (TRAIN + BENCH + DEMO) | aprobada |
| D2 | Comparar los tres enfoques de ausencia (E1/E2/E3) como experimento de tesis | aprobada |
| D3 | Estrategia de origen: explorar/relevar primero, decidir con tabla puntuada | aprobada |
| D4 | Obligatorios = calidad de anotación + licencia permisiva | aprobada |
| D5 | GT a nivel persona obligatorio solo para el rol BENCH | aprobada |
| D6 | `no_vest` no se entrena; E3 sí lo prueba por prompt | aprobada |
| D7 | Agregar `bare_head` como clase entrenable (E2) | aprobada |
| D8 | Deprecar (no borrar) vistas/splits actuales hasta tener reemplazo | aprobada |
| D9 | `bare_head` solo desde negativos explícitos; prohibido derivar `head − helmet` (G2) | aprobada |
| D10 | GT del BENCH desde anotaciones explícitas, no por asociación espacial (anti-circularidad, G1) | aprobada |
| D11 | Contrato de anotación v2 con matriz fuente×clase de exhaustividad (G4) | aprobada |
| D12 | Protocolo de medición con métricas/IoU/prompts/sinónimos congelados (G3) | aprobada |
| D13 | BENCH held-out respecto de TRAIN; control de fuga por escena (G5) | aprobada |
| D14 | Mínimos de balance de clases (TRAIN) y de poder estadístico (BENCH) (G6) | aprobada |
| D15 | Rúbrica operable (checklist N=50, umbral) + scoring como artefacto CSV (G7) | aprobada |
| D16 | Export por modelo: ODVG→GDINO/MM-GDINO, YOLO→YOLOE, COCO pivote (G8) | aprobada |
| D17 | Blurring de rostros por defecto en DEMO salvo licencia/consentimiento (G9) | aprobada |

> Defaults numéricos a confirmar antes de ejecutar: IoU 0.5 (§6.2), ≥150+150 por condición
> (§6.5), N=50 imágenes y umbral >15 % defectos (§7), muestra de auditoría ≥10 %/≥200 (§5.3).
