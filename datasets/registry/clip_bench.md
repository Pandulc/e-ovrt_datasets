# Registry — `clip_bench` (banco de clips con GT temporal)

Análogo de [`bench_v3.md`](bench_v3.md) para **video**. El bench de imágenes mide
percepción (mAP, AP@0.5); este banco mide **patrones de riesgo con GT temporal**:
precision/recall de episodios, `t_alert-system`, TTFD y SDR.

- **Estado:** `reportable` (los 47 clips en `gt_ready`) — **2026-08-09**. El lote de
  internet quedó CERRADO: 13 de 14 con GT; `v08_c01` excluido con causa (§1.1).
- **Manifest:** `datasets/processed/clip_bench/clip_bench_manifest.json`
  (`schema_version: clip_bench_manifest.v1`)
- **`manifest.yaml` sha256:** `299ccc19593361db…` — **freezes anteriores, todos
  verificables en git**: 34 clips del rodaje `cef5082e…` (commit `f7a27fe6`, el que
  citan T1/T2/D1/H1/G1/B1/R1–R6), 37 con estrato B `6b75ac6e…`, 38 con `v04_c02`
  `4437eb6d…`. El manifest solo crece; las filas del rodaje nunca cambiaron.
  Las campañas del rodaje (T1…R6) se congelaron contra el freeze de 34 y **no
  incluyen** el estrato B, por diseño. Las del estrato B (i1/i2, na1) corrieron su
  **gen. 3 el 2026-08-09 con los 13 clips** — el lote completo (doc 111).
- **Checksums:** `clip_bench.sha256` — verificar con
  `cd datasets/processed/clip_bench && sha256sum -c clip_bench.sha256`

## 1. Composición

| | | (rodaje solo, hasta 08-03) |
|---|---|---|
| Clips | **47**, todos con GT, todos `gt_ready` | 34 |
| Bloque | A (rodaje guionado 2026-07-25) 34 · **B (lote de internet) 13 de 14** | A 34 |
| Escenarios | P1:14 P2:5 P3:2 P4:2 P5:11 P6:3 P7:4 P8:1 P9:5 — **P1–P9 sin huecos** | P1:11 P2:5 P3:2 P4:2 P5:2 P6:2 P7:4 P8:1 P9:5 |
| Positivos / negativos / **soak** | 34 / **13** / **1** | 30 / 4 / 0 |
| Episodios | **40** — CR-01: 32, CR-02: 8 | 35 — CR-01 28, CR-02 7 |
| Duración total | 1.976.837 ms (**32 min 57 s**) | 1.072.736 ms (17 min 53 s) |
| Duración negativa | 915.901 ms (0,2544 h) | 128.834 ms (0,0358 h) |
| **Denominador FAR/hora** | **0,1027 h** (el soak `v06_c01`) | 0,0 h |

> **✎ 2026-08-09 — EL LOTE DE INTERNET QUEDÓ CERRADO: 13 de 14 con GT.** Entraron 8
> clips en dos tandas (7 el 08-09 + `v02_c01`): **2 positivos** (`v01_c02` evaluable;
> `v01_c01` **censurado** por A1 — su episodio arranca a 31,6 s en un clip de 37,2 s) y
> **6 negativos**. El tiempo negativo llega a **0,2544 h**, pero el **denominador de
> FAR/hora no se mueve**: ninguno alcanza los 5 min del gate de soak, así que suman
> control de FP, no denominador. Aporte cualitativo: `v04_c03` es **el único negativo
> nocturno del banco** y con él el eje nocturno llega a n=3.
>
> **`v08_c01` queda EXCLUIDO con causa** (decisión del usuario): el lote ya cumplió su
> función con 13 clips y anotar el 14º no cambia conclusiones. **No es un pendiente** —
> es cobertura no ejecutada con causa (doc 57 §7.6). Su `.mp4` y su pre-anotación siguen
> en disco; sin GT humano no es promovible y ninguna campaña lo toca. Ficha con el
> bloque `excluded:` en `datasets-videos/v08_c01.clip.yaml`.

> `v03_c02` (2026-08-07) **suma negativo pero no denominador**: 104.900 ms de obra real
> en cumplimiento que engordan la duración negativa (0,1548 → 0,1840 h) sin tocar el
> denominador de FAR/hora, que sigue siendo el único soak (≥5 min, doc 57 §3.2 G1).
> Su aporte es **control de falsos positivos**: cualquier alerta sobre él es un FP.

> **✎ 2026-08-07 — el banco tiene por primera vez un denominador de FAR/hora.**
> `v06_c01` (6:09,6 continuos) era el único candidato a soak por duración; su GT decía
> que tenía un episodio CR-02 y por eso no calificaba. La **revisión visual en CVAT
> determinó que ese episodio era un error de anotación** (la persona sí llevaba
> chaleco) y se corrigió con firma (`annotation.attribute_corrections`, doc 108 §6).
> El clip pasó a negativo/P5 y habilitó el denominador. **El FAR medido es malo**
> —**29,2 FA/hora en escena, 1.850,8 por sujeto**— y eso **precisa D-90.1 en vez de
> derogarla**: la cota "≤1 FA/hora" sigue exigiendo 3,0 h que el banco no tiene, pero
> ya no hace falta declarar la métrica no medible cuando el dato la refuta.

### 1.1 Estrato B — lote de internet (docs 102, 108, 110 y 111)

**Trece** de los 14 clips de obra real NO guionada (canal `@HospitalConstruction`,
§Material de VIDEO de `license_registry.md`), con GT humano de CVAT. **Levantan L4.**
El lote está **CERRADO**: el 14º (`v08_c01`) queda excluido con causa (abajo).

| clip | duración | escenario | GT | luz |
|---|---|---|---|---|
| `v01_c01` | 37.200 ms | P1 | 1 ep CR-01 `31.567 → 37.200 ms` — **CENSURADO** (A1) | diurna |
| `v01_c02` | 32.767 ms | P1 | 1 ep CR-01 `0 → 15.633 ms` — evaluable, **sin pre-roll** | diurna |
| `v02_c01` | 48.900 ms | P5 | negativo — sin un solo atributo en `false` en los 7 tracks | diurna |
| `v03_c01` | 22.000 ms | P5 | negativo | diurna |
| `v03_c02` | 104.900 ms | P5 | negativo — tras corrección firmada | diurna |
| `v04_c01` | 19.067 ms | P1 | 1 ep CR-01 `3.967 → 17.967 ms` | **nocturna** |
| `v04_c02` | 28.000 ms | P6 | 2 ep (CR-01+CR-02) `0 → 23.833 ms`, mismo sujeto | **nocturna** |
| `v04_c03` | 32.133 ms | P5 | negativo — **el único negativo nocturno del banco** | **nocturna** |
| `v05_c01` | 78.500 ms | P5 | negativo — el negativo más largo después del soak, 17 tracks | diurna |
| `v06_c01` | 369.567 ms | P5 | negativo — **el clip SOAK** — tras corrección firmada | diurna |
| `v07_c01` | 26.867 ms | P5 | negativo | diurna |
| `v09_c01` | 45.167 ms | P5 | negativo | diurna |
| `v10_c01` | 59.033 ms | P5 | negativo — fachada en altura (arnés, no chalecos) | diurna |

**5 episodios**, de los cuales **4 evaluables** (el de `v01_c01` está censurado: arranca
a 31,6 s en un clip de 37,2 s y CR-01 exige llegar a 45,6 s). Dos llevan aviso de
**pre-roll** (`v01_c02` y `v04_c02`, onset en t=0): su TTFD es artefacto del recorte.

**La curación de escenarios acertó 7 de 13.** Se fijaron antes de anotar y el GT los
desmintió en la mitad: `v04_c01` P8→**P1**, `v04_c02` P5→**P6**, `v01_c01` y `v01_c02`
P5→**P1**, y `v06_c01`/`v03_c02` recorrieron P5→positivo→**P5** (vuelven a la etiqueta
curada, pero sólo después de una corrección firmada). Los 6 que acertaron de entrada son
negativos. D-90.1 ya advertía que `scenario` en este lote era expectativa, no hecho.

**El 14º clip, `v08_c01`, NO se anota — exclusión declarada (usuario, 2026-08-09).**
50,2 s diurnos, expectativa de curación `P5`. Causa: el lote ya cumplió su función
(levantar L4) con 13 clips, y el 14º no cambia conclusiones — sería más tiempo negativo
corto para un denominador que no depende de él. **No es un pendiente: es cobertura no
ejecutada con causa** (doc 57 §7.6). Su `.mp4` y su pre-anotación quedan en disco por si
alguna vez se decide anotarlo; sin GT humano no es promovible y ninguna campaña lo toca.
Su ficha lleva el bloque `excluded: true` con firma y fecha.

⚠️ **Dos revisiones visuales pendientes** (anotadas en sus `clip.yaml`): el sujeto del
episodio de `v01_c01` está dentro del edificio y a contraluz —la cabeza no es claramente
observable, misma familia que `v03_c02`—, y el de `v01_c02` aparenta cabeza descubierta
con un compañero con casco al lado (el `false` es plausible). El GT vigente respeta lo
que marcó el anotador.

**Corrección firmada de `v06_c01` (2026-08-07, doc 108 §6).** La revisión visual en
CVAT del track 110 determinó que el `has_vest: false` de los frames 10272–10665 era
**error de anotación**: la persona sí llevaba chaleco. Se corrigió con
`annotation.attribute_corrections` (mecanismo nuevo: pisa un valor explícito del
anotador, con `previous_value` verificado, `track_id` obligatorio y firma) y el clip
pasó a negativo. Los otros dos tramos que la auditoría había marcado (`unknown` en
9935–10205 y 10207–10271) quedaron **confirmados como incertidumbre legítima**: el
sujeto está al borde del plano o detrás de rejas.

**Corrección firmada de `v03_c02` (2026-08-07, doc 110).** El export crudo dejaba
**1 episodio CR-01 de 4.000 ms EXACTOS** (16.400 → 20.400 ms), sostenido por un solo
track: el **operador sentado en la cabina de la excavadora** (track 0, entra en el frame
492). La revisión visual determinó dos cosas sobre ese sujeto: lleva **chaleco naranja
de alta visibilidad** claramente visible a través del vidrio (el `has_vest: false` era
error de anotación) y su **cabeza no es observable en ningún frame** — el marco y el
reflejo de la cabina la tapan, así que el `has_helmet` venía partido en conjeturas
(`false` en 190 cajas, `true` en 12). Se corrigió con **4 entradas** de
`attribute_corrections` (una por atributo y tramo, porque el guard de `previous_value`
exige coincidencia caja por caja): vest `false→true` y helmet `false/true→unknown` en
las 202 cajas del track. El clip pasó a **negativo/P5**. Es la primera vez que el
mecanismo se usa para resolver a **`unknown`** en vez de a un valor explícito: la
incertidumbre no fabrica una violación, y tampoco un cumplimiento. **El episodio
eliminado era el positivo más frágil del banco** (4.000 ms contra un umbral de 4.000 ms,
todo él sobre atributos no observables), así que sacarlo endurece el banco.

## 2. Procedencia

1. **Rodaje** 2026-07-25, Bloque A, guionado (doc 69 = guion operativo; fichas por
   clip en `datasets-videos/docs/ficha-eventos-rodaje.md`). Fuentes: OAK-D PoE y DVR.
   Consentimientos de los participantes: administrativo del rodaje.
2. **Etapa 0** — `prepare_clip.sh`: normalización a CFR sin audio + `.info.json`
   (fps entero, `n_frames`, sha256). Sin esto el mapeo frame↔ms no es exacto.
3. **Pre-anotación** — `preannotate_video` (GDINO-**base**, más fuerte que el tiny
   evaluado: anti-circularidad) + ByteTrack.
4. **Corrección humana en CVAT** — proyecto `TFG`, equipo del usuario. Del **rodaje**
   el export fue a nivel PROYECTO, que numera los frames en un espacio global y
   continuo; se dividió con `split_cvat_project.py` (rebase de frames +
   `<meta><task><size>` para reactivar el guard I2). Sin ese paso el GT sale
   **negativo en silencio** (doc 80 §2). ⚠️ Del **estrato B y el piloto** los exports
   llegaron a nivel **TASK** y `split_cvat_project.py` NO se aplica: sería el error
   simétrico. **Mirar `meta/task` vs `meta/project` antes de decidir** (doc 102 §1.1).
5. **Adjudicación de huecos `unknown`** — 6 clips del rodaje (limitación L3), vía
   `apply_adjudications.py`, que **solo convierte `unknown`** y se niega a pisar
   valores explícitos del anotador.
6. **Corrección de valores explícitos** (2026-08-07, `v06_c01` y `v03_c02`) —
   `apply_attribute_corrections.py`, mecanismo aparte y con más ceremonia (8 campos,
   `track_id` obligatorio, `previous_value` verificado, idempotente). Es el único
   camino por el que un valor `true`/`false` del anotador puede cambiar, y exige firma
   + rationale en el `clip.yaml`. Ver §1.1.
7. **Derivación** — `derive_clip_gt.py`, pattern set **`cr01_cr02_v2`**
   (CR-01 4000 ms / CR-02 7000 ms). Nunca v1: produce falsos `missed`.
8. **Promoción y ensamblado** — `promote_clip.py` (estado derivado de los
   artefactos reales, nunca impuesto) + `build_clip_bench.py`. ⚠️ `promote_clip` hace
   round-trip del YAML y **borra los comentarios de `manifest.yaml`** (pasó 3 veces el
   2026-08-06/07): revisar el bloque del final tras cada promoción.

### 2.1 Campañas que consumen este banco

| estrato | Nivel B | Nivel A |
|---|---|---|
| A (rodaje, 34) | `results/clip_bench/` — T1, T2, D1, H1, G1, B1, R1–R6 (congeladas contra el freeze `cef5082e`) | — |
| B (internet, **4 de 5**) | `results/clip_bench/i1_…_scene_internet` · `i2_…_subject_internet` | `results/bench_nivel_a/na1_gdinotiny560_v2short_video` |
| Piloto (4, `_retired/`) | **no aplica** (censura A1) | ídem `na1_…` |

⚠️ **`v03_c02` está en el banco pero en NINGUNA campaña**: entró el 2026-08-07 después
de que i1/i2/na1 se congelaran. Correrlo es trabajo pendiente (doc 110 §4) y **no
retoca** las cifras publicadas de i1/i2/na1: se reportan como fila aparte o se re-corre
la campaña completa contra el freeze nuevo, nunca se mezclan dos freezes en una tabla.

Artefactos supersedidos y por qué: `docs/operacion/datos/109-SUPERSEDIDOS.md`.

### 2.2 Fuente de verdad de las anotaciones (decisión del usuario, 2026-08-09)

**La anotación versionada en este repo es la fuente de verdad. CVAT no lo es.**

| ruta | rol |
|---|---|
| `datasets/processed/clip_bench/annotations/<clip>.xml` | **autoritativa** — versionada en git, es la que produjo el GT del banco |
| `datasets-videos/corrected/<clip>.xml` | working copy, **gitignorada**; se puede regenerar |
| CVAT (`10.147.17.189:8080`) | herramienta de anotación; su estado **puede diverger** y no se sincroniza hacia atrás |

**Por qué la distinción importa, con un caso real.** Las correcciones de `v03_c02` se
hicieron **por orden del usuario, sobre la anotación del repo** (`decided_by:
simonll4`); CVAT nunca se modificó. Cuando el 2026-08-09 llegó un re-export de ese
clip, vino —como corresponde— con el XML **anterior** a las correcciones
(`has_vest: false` ×202, `has_helmet` partido en 190 `false` / 12 `true`). Integrarlo
habría revertido una decisión firmada y devuelto al banco un episodio CR-01 falso
**en silencio**, porque toda la cadena aguas abajo habría quedado consistente consigo
misma. Se detectó al diffear contra el banco antes de tocar nada.

**Esto va a volver a pasar y es lo esperable**, no una anomalía: todo clip con
correcciones firmadas se re-exporta sin ellas, porque la decisión vive en el repo y no
en la herramienta de anotación. Por eso el chequeo de abajo no es opcional.

**El guard, para que no dependa de que alguien se acuerde:**

```bash
python3 datasets/scripts/videogt/apply_attribute_corrections.py \
    --xml datasets/processed/clip_bench/annotations/<clip>.xml \
    --clip-yaml datasets/processed/clip_bench/meta/<clip>.clip.yaml --check
```

No escribe nada; sale **1** si alguna corrección firmada no está aplicada. Correrlo
sobre todo clip que declare `attribute_corrections` **antes de re-derivar** cualquier
GT que venga de un export nuevo. Hoy aplica a `v03_c02` (4 correcciones) y `v06_c01`
(1); ambos verificados verdes.

**Corolario para el flujo de trabajo:** un re-export de CVAT no es una actualización
automática. Es un **candidato** que hay que diffear contra la anotación del banco; si
difiere en un tramo corregido, manda el banco.

## 3. Limitaciones declaradas

Se declaran acá **antes** de reportar resultados, no se descubren después.

### L1 — FAR/hora: de *no reportable* a **medida y desfavorable** (D-90.1 2026-08-04, precisada 2026-08-07)

El denominador de FAR/hora exige negativos de ≥5 min (doc 57 §3.2, gate G1).

> **✎ 2026-08-07 — ESTA LIMITACIÓN CAMBIÓ DE NATURALEZA.** El banco **ya tiene** un
> clip soak (`v06_c01`, 0,1027 h) desde que la corrección de su GT lo volvió negativo
> (§1.1). FAR/hora **es medible**, y lo medido es **29,2 FA/hora en escena y 1.850,8
> por sujeto** sobre obra real en cumplimiento (cifras corregidas el 2026-08-09:
> el agregador mezclaba bases en `far_per_hour` — doc 111 §6). La determinación D-90.1 **se precisa,
> no se deroga**: su argumento —que ningún denominador alcanzable sostiene la cota
> "≤1 FA/hora", que exigiría 3,0 h— sigue en pie. Lo que ya no corresponde es
> declarar la métrica *no reportable*: se reporta el valor medido, con su denominador
> declarado y su intervalo enorme, y se dice que **refuta** la operabilidad en vez de
> quedar en silencio. Todo lo que sigue en esta sección describe el estado anterior y
> se conserva por trazabilidad.

**Estado anterior (hasta 2026-08-06):** el banco no tenía ningún negativo de ≥5 min;
los 4 negativos sumaban 0,0358 h y **no entraban al denominador** (el manifest lo
declara explícito en `far_denominator_basis`).

**Determinación (doc 90 D-90.1 del repo `docs`):** no se trata de un pendiente sino de
un límite del material. Con 0 FP y la regla de 3 hacen falta **3,0 h** de video en
cumplimiento anotado para poder afirmar "FAR ≤ 1 FA/hora" (umbral **ilustrativo**: el
proyecto no pre-registró un objetivo de FAR — el punto es que ninguna cota alcanzable
sostiene una afirmación); el banco alcanza **0,10 h** con el clip soak previsto
(6,2 min del lote de internet) y como mucho **0,26 h** si se agregaran todos los
negativos cortos. Una cota de 11–30 falsas alarmas por hora no sostiene ninguna
afirmación operativa.

**Qué se reporta en su lugar:** el **control de negativos** por campaña. Es evidencia
**comparativa pareada** — las mismas escenas, el mismo GT, condiciones idénticas para
todas las combinaciones — y en ese rol discrimina: T1, T2, G1 y B1-eind dan **0 FP de
4 clips**; D1, H1 y B1-`bare_head` dan 2–3. Lo que NO es: una tasa absoluta de falsas
alarmas (2,1 min no cuantifican una tasa — esa pregunta queda declarada acá, como L1).
El clip soak, cuando esté, se reporta como el único con denominador temporal y **como
contexto de la incertidumbre**, nunca como rendimiento.

**Corrección al doc 57:** ese doc estima el material soak en *"≈0 anotación"*. Es falso
en la práctica: un soak de obra en cumplimiento tiene gente en cuadro y certificar que
nadie viola durante minutos exige trackear a todos frame a frame (el `--allow-empty` de
`derive_clip_gt` cubre el caso contrario: clips **sin personas**). Medido: el clip de
6 min lleva más de una jornada. Un modo "negativo atestiguado" (revisión humana con
protocolo, sin cajas) lo abarataría — queda como trabajo futuro.

### L2 — Sin doble anotación: no hay kappa (DECISIÓN, no pendiente)

`double_annotation_ratio: 0.0` frente al objetivo ≥0,2 del doc 58 §B.3
(≈7 clips re-anotados por una segunda persona).

**Decisión del equipo, 2026-08-03: no se ejecuta.** Motivo: el proyecto lo lleva
un equipo de 3 personas y el presupuesto de tiempo hasta la defensa (~fines de
septiembre 2026) no lo admite. No es un ítem pendiente que se vaya a cerrar: es
una limitación asumida.

**Consecuencia metodológica, que hay que escribir en el informe:** no existe
medida de acuerdo inter-anotador (kappa) para este GT, así que **la
confiabilidad de la anotación no está cuantificada**. Los números de
precision/recall del banco se leen como "contra el criterio de un anotador",
no "contra un GT de confiabilidad medida". Mitigaciones parciales que sí
existen y conviene citar:

- el GT no es de anotación libre: sale de una **pre-anotación automática
  corregida**, lo que acota la deriva subjetiva del trazado de cajas;
- las **fichas del rodaje** (`ficha-eventos-rodaje.md`, registradas el 25/07,
  independientes de la anotación) concuerdan con los episodios derivados dentro
  de ~1 s en la gran mayoría de los clips — es una verificación cruzada, no un
  kappa;
- el rodaje es **guionado**: qué condición ocurre en cada toma estaba decidido
  antes de filmar, así que la identidad de los episodios no depende del criterio
  del anotador, solo sus bordes.

### L3 — Seis clips con huecos `unknown` adjudicados (F-GT1)

En `a_p1_c09`, `a_p1_c10`, `a_p1_c11`, `a_p1_c12` (CR-01) y `a_p2_c04`,
`a_p2_c05` (CR-02) el anotador marcó el atributo `unknown` durante 3,4–5,9 s en
medio de una violación: el actor queda **visible pero ocluido** (en P1 mete la
cabeza detrás de una caja; en P2 la caja que carga le tapa el torso).

Frame a frame ese `unknown` es la anotación correcta. Pero el GT del banco
declara el **estado real**, y dejarlo como `unknown` partía cada episodio en dos:
el motor —que ve una persona detectada de forma continua— sostiene UNA alerta, y
el evaluador contaría el segundo tramo como `missed`, deprimiendo el recall por
un artefacto de observabilidad (misma clase que F-DR9).

Se adjudicó `false` en los 6, con firma y justificación en
`annotation.unknown_adjudications` de cada `clip.yaml` (propagado al GT del
banco, auditable). Aplicado con `apply_adjudications.py`, que **solo convierte
`unknown`** y se niega a pisar un valor explícito del anotador. Efecto: 6 clips
2→1 episodios (41→35), y 5 avisos de censura por dimensionamiento desaparecen.

**Consecuencia:** 6 de los 35 episodios (17%) tienen bordes que dependen de un
juicio declarado sobre tramos no observables, no solo de la imagen.

### L4 — Un solo bloque, material guionado — **PARCIALMENTE LEVANTADA (2026-08-06)**

34 de los 39 clips son Bloque A: **rodaje guionado**, un escenario controlado,
mismos actores y locación. Desde el 2026-08-06/07 hay **5 clips de obra real no
guionada** (estrato B, §1.1) con GT humano, licencia registrada, **3 episodios
evaluables** y **el único clip soak del banco**: la generalización a obra real deja de estar sin medir,
pero se mide con **n = 3 episodios**, así que la limitación se reformula en vez
de desaparecer:

> el banco mide obra real, con un intervalo de confianza que hay que declarar. Las
> campañas del estrato B se reportan **como fila aparte con desglose** (D-90.6),
> nunca fusionadas al agregado del rodaje.

El bench de imágenes `bench_v3` sí cubre 3 fuentes independientes con n grande.

El otro clip de obra real que existía (`cb_b01_p7`) fue **retirado** el 2026-08-03:
licencia/consentimiento sin registrar y GT producido por IA. Motivo completo en
`datasets/processed/clip_bench/_retired/cb_b01_p7/MOTIVO.md`. El estrato B no
hereda ese problema: licencia registrada (§Material de VIDEO de
`license_registry.md`) y GT humano de CVAT.

### L5 — Escenarios desbalanceados

P1 aporta 12 clips y P8 solo 1. Los agregados por condición están dominados por
P1/P2 (17 de 39). **Reportar por escenario además del agregado**, igual que la
regla de `bench_v3` para estratos — y, desde que hay dos bloques, **también por
bloque**.

## 4. Regenerar

```bash
cd e-ovrt_datasets
# (1) dividir el export de proyecto de CVAT — solo rodaje
python3 datasets/scripts/videogt/split_cvat_project.py \
    --xml ../rodaje-anotado/annotations.xml \
    --out-dir datasets-videos/corrected --match '^a_p[0-9]+_c[0-9]+$'
# (2) aplicar adjudicaciones declaradas + (3) derivar + (4) promover
for y in datasets-videos/a_p*.clip.yaml; do id=$(basename "$y" .clip.yaml)
  python3 datasets/scripts/videogt/apply_adjudications.py \
      --xml datasets-videos/corrected/$id.xml --clip-yaml "$y"
  python3 datasets/scripts/videogt/derive_clip_gt.py --xml datasets-videos/corrected/$id.xml \
      --clip-yaml "$y" --info datasets-videos/clips/$id.info.json \
      --out datasets-videos/gt/$id.json
  python3 datasets/scripts/bench/promote_clip.py --clip-id $id
done
# (5) validar y congelar
python3 datasets/scripts/bench/validate_clip_gt.py --gt-dir datasets-videos/gt
python3 datasets/scripts/bench/build_clip_bench.py
```

Estrato B (exports a nivel **TASK**: NO pasa por `split_cvat_project.py`), con el paso
extra de corrección de valores explícitos:

```bash
cd e-ovrt_datasets
id=v03_c02
cp <export-de-cvat>/annotations.xml datasets-videos/corrected/$id.xml
python3 datasets/scripts/videogt/apply_attribute_corrections.py \
    --xml datasets-videos/corrected/$id.xml --clip-yaml datasets-videos/$id.clip.yaml
python3 datasets/scripts/videogt/derive_clip_gt.py --xml datasets-videos/corrected/$id.xml \
    --clip-yaml datasets-videos/$id.clip.yaml --info datasets-videos/clips/$id.info.json \
    --out datasets-videos/gt/$id.json
python3 datasets/scripts/bench/validate_clip_gt.py --gt-dir datasets-videos/gt
python3 datasets/scripts/bench/promote_clip.py --clip-id $id --lab-dir datasets-videos
python3 datasets/scripts/bench/build_clip_bench.py
cd datasets/processed/clip_bench && sha256sum -c clip_bench.sha256
```

Determinista: mismo export + mismos `clip.yaml` → mismo `manifest.yaml` sha256. El
`apply_attribute_corrections` es idempotente y **falla cerrado** si el export cambió por
debajo de una corrección firmada, así que la cadena se puede re-correr entera sin miedo.
