# `bench_v3` — bench de imágenes estratificado (2026-07-23)

Ampliación de `bench_obra` (147 imgs) con dos fuentes independientes auditadas: **CHV**
(académica, obra real) y **SHEL5K** (Mendeley, CC BY 4.0). Objetivo: reducir el intervalo de
confianza de las métricas por clase (`docs/operacion/66` del repo `docs`, plan de
ampliación) sin perder la trazabilidad de qué imagen viene de dónde.

## Cómo se arma

```bash
python3 datasets/scripts/curate/build_bench_v3.py
```

Fusiona por referencia los 4 COCOs curados de `processed/coco/bench/curated/` (ids
remapeados a un espacio global único; cada imagen conserva su campo `stratum`), y emite:

- `bench_v3.json` — el COCO fusionado, 4 clases canónicas (person/helmet/vest/bare_head).
- `bench_v3_manifest.json` — conteos por estrato + sha256 de cada fuente y del bench
  fusionado (congelamiento: cualquier cambio en una fuente cambia el sha256 visible).

### Cadena completa (de raw a bench_v3) — ✎ 2026-08-19

`build_bench_v3.py` es el ÚLTIMO eslabón: fusiona 4 COCOs que ya existen. Quién produce
cada uno:

| Artefacto | Generador | Fuente |
|---|---|---|
| `construction_site_safety_bench_obra_{test,val}.json` (147) | `curate/build_bench_obra.py` | `processed/coco/bench/construction_site_safety_bench.json` |
| `bench_stratum_chv.json` (1.330) | `curate/build_bench_strata.py` | `processed/coco/canonical_v2/chv/{train,val,test}.json` |
| `bench_stratum_shel5k.json` (5.000) | `curate/build_bench_strata.py` | `processed/coco/canonical_v2/shel5k/{train,val,test}.json` |
| `bench_v3.json` + manifest (6.477) | `curate/build_bench_v3.py` | los 4 anteriores |

Aguas arriba, las vistas `canonical_v2` y `bench` salen de
`convert_datasets.py --views canonical_v2` sobre `datasets/raw/` (gitignoradas, ver
`documentation/guia_conversiones.md`).

### Verificar el freeze

El script escribe exactamente la serialización que hashea (`sort_keys=True`), así que la
verificación es directa con la herramienta obvia:

```bash
sha256sum datasets/processed/coco/bench/curated/bench_v3.json
# debe dar el `bench_v3_sha256` del manifest; ídem cada fuente vs `source_sha256`
```

Pinneado en `datasets/tests/test_bench_v3_freeze.py` (sha del agregado, sha de las 4
fuentes y conteos congelados; los tests se skippean si los artefactos no están en disco).
Nota histórica: hasta 2026-07-29 el JSON estaba escrito sin `sort_keys` y `sha256sum`
NO reproducía el `bench_v3_sha256` (había que re-serializar ordenado); el freeze era
válido igual — las fuentes coincidían byte a byte — pero no verificable directo. El
contenido del bench no cambió al alinearlo (mismos conteos, mismo `bench_v3_sha256`:
`4557024e…`), solo el orden de claves del archivo.

### Los estratos `chv` y `shel5k` ya tienen generador — ✎ 2026-08-19

Hasta hoy la cadena tenía un eslabón manual: `docs/operacion/66` §B5 declaraba los
estratos `chv`/`shel5k` como "COCOs por estrato fusionados", pero **ningún script
commiteado los escribía** (a diferencia de `bench_obra`, que sí tenía
`build_bench_obra.py`). Si `bench_v3` hubiera que rearmarlo desde las fuentes, ese paso
no era reproducible. Ahora sí:

```bash
# verificar que los congelados se reproducen (no escribe nada)
python3 datasets/scripts/curate/build_bench_strata.py --verify

# regenerar a un directorio propio
python3 datasets/scripts/curate/build_bench_strata.py --out-dir /tmp/strata
```

**Estado de verificación (2026-08-19): PASS en los dos estratos, byte a byte.** Regenerar
desde `processed/coco/canonical_v2/` da exactamente los sha256 congelados —
`chv` `6d15ff9b…`, `shel5k` `bf35f63b…` — o sea, los mismos que el `source_sha256` del
manifest de bench_v3. No quedó ninguna parte no reproducible: la fusión no escondía
ningún paso manual.

Procedencia REAL, medida sobre los artefactos (no declarada de memoria): cada estrato es
la **concatenación de los tres splits `canonical_v2` del dataset en el orden
`train, val, test`** — chv 1.064 + 133 + 133 = 1.330 imgs / 9.209 anns; shel5k
3.500 + 750 + 750 = 5.000 imgs / 45.395 anns. Los ids de imagen y anotación se remapean a
1..N en ese orden de recorrido; `info` y `licenses` del COCO fuente se descartan; **no hay
filtrado, muestreo ni semilla propia** (entra el 100% de cada split — la semilla fija 42
que sí existe está aguas arriba, en el split `custom_seeded` de shel5k dentro de
`convert_datasets.py`). Serialización: `json.dumps` pelado, sin `indent`, sin `sort_keys`,
sin newline final — distinta a propósito de la de `bench_v3.json` (`sort_keys=True`),
porque el `source_sha256` hashea los bytes del estrato tal como están en disco.

Los artefactos congelados **no se tocaron**: el script escribe a un directorio temporal
por defecto y se niega a escribir dentro de `curated/` salvo `--allow-frozen-overwrite`.
Pinneado en `datasets/tests/test_bench_strata.py` (13 tests: 9 sintéticos de la fusión +
byte-identidad y conteos por estrato, skippeados si falta la fuente `canonical_v2` —
gitignorada — o el congelado). ✎ 2026-08-28: el archivo tiene **11** `def test_` (no 13; la
cifra no afecta a nada — `docs/operacion/130`).

**Discrepancia doc↔artefacto encontrada: ninguna.** Los conteos de doc 66 §B5 y de la
tabla de Composición de abajo coinciden con lo medido.

## Composición

| Estrato | Origen | Imágenes | Aporta |
|---|---|---|---|
| `bench_obra_test` + `bench_obra_val` | `construction_site_safety` curado (doc 63) | 147 | núcleo con pasada visual muestral, todas las clases con negativos explícitos |
| `chv` | CHV (académico, GitHub ZijianWang; grant "open for free use" de los autores, SIN licencia formal — cita obligatoria `wang2021ppe`, imágenes no redistribuibles; verificado 2026-07-29, ver `license_registry.md`) | 1.330 | 2ª fuente person/helmet/vest; **mejor AP de vest medido en el proyecto** (0.55–0.58) |
| `shel5k` | SHEL5K (Mendeley 9rcv8mm682 v4, CC BY 4.0) | 5.000 | 3ª fuente; **bare_head nativo** (6.120 instancias vs 61 del núcleo) + `person_gt_shel5k.json` (5.248 violadores CR-01) |
| **Total** | | **6.477** | |

> ✎ **2026-08-28 — `stratum` tiene CUATRO valores, no tres (`docs/operacion/130`, R-22).**
> En `bench_v3.json` y en `manifest.strata` los valores son `bench_obra_val` (85) ·
> `bench_obra_test` (62) · `chv` (1.330) · `shel5k` (5.000). Cualquier agrupación por
> `stratum` devuelve **4 filas**; los "3 estratos" de este doc y del informe son una
> **fusión declarada** de los dos de obra en `bench_obra` (147). Al citar, explicitar la fusión.
>
> ✎ **2026-08-28 — rol TRAIN de `chv` es histórico; el fine-tuning lo EXCLUYÓ (`docs/operacion/130`, R-02).**
> `chv` fue fuente TRAIN sólo en la vista `train_v2` (archivada el 2026-08-15). El fine-tuning
> efectivo (`finetuning_v1`, T1 job `1167640` y T2 job `1167982`) **excluyó `chv` por
> anti-leakage**: el 100 % de sus 1.330 imágenes es estrato de este bench. Entrenó
> `construction_site_safety` 2.203 + `ppe_siabar` 743 = **2.946** train (483 val). Fuente:
> `finetuning/manifests/finetuning_v1.summary.json` del experimental-setup y `docs/operacion/100` §V2.

## Qué anota cada fuente y cómo se agrega — ✎ 2026-11-23

Las tres fuentes **no anotan las mismas clases** ni en cantidades parecidas. Eso define cómo
se lee cualquier número del bench.

| Clase | `bench_obra` (147) | `chv` (1.330) | `shel5k` (5.000) | Imágenes donde se evalúa | Fuente que domina |
|---|---|---|---|---|---|
| `person` | 262 | 3.887 | 20.023 | 6.477 | `shel5k`, 83 % |
| `helmet` | 159 | 3.538 | 19.252 | 6.477 | `shel5k`, 84 % |
| `vest` | 79 | 1.784 | — | 1.477 | `chv`, 96 % |
| `bare_head` | 61 | — | 6.120 | 5.147 | `shel5k`, 99 % |
| violadores CR-01 (`person_gt`) | 60 | — | 5.248 | — | `shel5k`, 99 % |

**Por qué tres fuentes.** Ninguna alcanza sola. `bench_obra` anota las cuatro clases, pero
con 79 `vest` y 61 `bare_head`. `chv` suma 1.784 `vest` y no anota `bare_head`. `shel5k`
suma 6.120 `bare_head` y no anota `vest`.

**Cómo se evalúa.** Es la regla que hace válido al bench:

1. Cada estrato se corre y se evalúa **por separado**, contra su propio COCO curado.
2. Una clase que el estrato no anota da AP `None` (`n_gt = 0` en `evaluate_bench.py`). No
   cuenta como cero, y las detecciones de esa clase sobre ese estrato **no cuentan como
   falsos positivos**: la referencia no puede decir si son correctas. Es el criterio de los
   bancos de anotación federada, como LVIS (Gupta et al., 2019): cada categoría se mide solo
   donde está anotada.
3. El AP de cada clase en el bench es el promedio de los estratos que la anotan, ponderado
   por `n_gt` (`curate/bench_v3_report.py`, `weighted_map50`).
4. El mAP50 agregado es la media simple de las cuatro clases.

**Qué es entonces el agregado.** Clase por clase, casi una sola fuente: el AP de `vest` del
bench es el de `chv`, y el de `bare_head` y el recall CR-01 son los de `shel5k`. `bench_obra`
pesa entre el 0,7 % y el 4,2 % según la clase. El «n = 6.477» vale para `person` y `helmet`;
`vest` se mide sobre 1.477 imágenes y `bare_head` sobre 5.147. Por eso el agregado nunca se
cita solo.

**Por qué no evaluar todo junto.** Medido con la combinación de referencia
(`gdino-tiny-560`): con una sola curva por clase sobre los estratos que la anotan, `vest` da
0,551 y `bare_head` 0,110. Si entraran los cuatro estratos sin distinguir, darían 0,331 y
0,076. La diferencia son 6.193 detecciones de `vest` sobre `shel5k` y 2.192 de `bare_head`
sobre `chv`, que pasarían a ser falsos positivos solo porque esa fuente no anota la clase.

**El orden de las combinaciones no depende de la regla** (mAP50):

| Regla de agregación | `gdino-tiny-560` | `gdino-base-560` | `yoloe-26x` |
|---|---|---|---|
| Oficial: ponderado por `n_gt` | 0,551 | 0,525 | 0,442 |
| Cada fuente pesa lo mismo | 0,545 | 0,496 | 0,437 |
| Una sola curva por clase, en los estratos que la anotan | 0,535 | 0,519 | 0,436 |
| Solo `bench_obra` (147) | 0,503 | 0,464 | 0,405 |

**La cifra de `bench_obra` usa otra regla.** El mAP50 de `bench_obra` que se publica (0,503
para la combinación de referencia) es el promedio de sus dos particiones ponderado por
**imágenes** (62 y 85), no por `n_gt` como el agregado. Con las 147 imágenes en una sola
curva da 0,511; el orden es el mismo. Al citar esa cifra, decir la regla.

El análisis, sus intervalos de confianza y el script que lo reproduce están en el repo `docs`:
`operacion/147` y `operacion/datos/147-banco-de-imagenes-agregacion/`.

## Salvedades por estrato (no se ocultan, se reportan)

- **El mAP50 por estrato no se compara entre estratos** (✎ 2026-11-23): promedia cuatro
  clases en `bench_obra` y tres, distintas, en los otros dos (`chv` sin `bare_head`, que es
  la clase más difícil; `shel5k` sin `vest`). Con la combinación de referencia da 0,503 ·
  0,767 · 0,537. Con las dos clases que anotan los tres (`person` y `helmet`) da 0,733 ·
  0,874 · 0,739: en `bench_obra` y en `shel5k` rinde parecido, y en `chv` mejor.
- `bench_obra`: pasada visual **muestral** (36/147), no exhaustiva — mismo GT desde Sprint 2.
- `bench_obra` · **la caja de `bare_head` no es la misma que en `shel5k`** (✎ 2026-11-23). La
  clase `NO-Hardhat` de la fuente cubre la parte superior de la cabeza; la clase `head` de
  SHEL5K, la cabeza entera, que es lo que dibujan los modelos. Medido sobre la referencia: el
  alto de la caja es 0,12 del alto de la persona en `bench_obra` (menos que el de su caja de
  casco, 0,14) y 0,18 en `shel5k` (más que el de su casco, 0,15). Medido sobre las
  detecciones centradas en una caja de referencia: su área es 1,85 a 1,99 veces la de la
  referencia en `bench_obra` y 1,01 a 1,09 veces en `shel5k`. Consecuencia: el AP@0,5 de
  `bare_head` en `bench_obra` (≈ 0,02) **subestima** lo que se detecta. Con la combinación de
  referencia, de 61 cajas hay 8 aciertos y otras 11 con una detección de IoU entre 0,3 y 0,5.
  El recall CR-01 no depende de esa caja (usa el centro de la detección en la región de
  cabeza) y da 24 de 60.
- `chv`: dominio mixto obra/industrial-adyacente (scoring original: "parcial"); algunas
  imágenes de stock con watermark. Sin negativos explícitos ⇒ no aporta CR-01/CR-02.
- `shel5k`: resolución uniforme 416×416 (✎ 2026-08-28: **aproximado, no literal** — medido
  sobre el JSON: 416×415 en 2.461 imgs · 416×416 en 2.192 · 415×416 en 324 · 415×415 en 23;
  `docs/operacion/130`) (preprocesado Roboflow — objetos gruesos, "obra" en
  sentido amplio: incluye industria/mantenimiento, no solo construcción civil);
  mirror-padding horneado en ~2–10% de las imágenes con GT sobre las franjas espejadas;
  `has_vest` no anotado (person_gt_shel5k solo cubre CR-01, nunca CR-02).
- `shel5k` · **`person` no está anotada de forma exhaustiva** (✎ 2026-11-23). 4.395 de sus
  25.372 cabezas anotadas (`helmet` o `bare_head`), el 17,3 %, no tienen caja de persona; en
  `bench_obra` son el 4,5 % y en `chv` el 3,1 %. Una persona real sin caja convierte en falso
  positivo a la detección que la encuentra, así que el AP de `person` en `shel5k` es una cota
  inferior. Afecta a todas las combinaciones por igual: de las detecciones de `person` lejos
  de toda persona anotada, caen sobre una de esas cabezas 779 de 3.160 con `gdino-tiny-560` y
  707 de 2.825 con `yoloe-26x`. Tampoco entran al `person_gt`: los 5.248 violadores CR-01 son
  las personas anotadas sin casco, no las 6.120 cabezas descubiertas.

## Uso

Reportar SIEMPRE por estrato y agregado (nunca solo el agregado): un modelo puede rendir
distinto en 416×416 uniforme que en `bench_obra` de resolución variable. El agregado
ponderado por n es el número de cierre; el desglose por estrato es el diagnóstico.

Evaluación del media-plane contra el bench completo:

```bash
python -m eovrt_media.tools.evaluate --run runs/<run_id> \
  --bench-coco ../e-ovrt_datasets/datasets/processed/coco/bench/curated/bench_v3.json
```

> ✎ **2026-11-23 — una corrida por estrato, nunca una sola con todas las imágenes.** El
> comando de arriba es correcto cuando la corrida procesó **un** estrato: el evaluador
> restringe la referencia a las imágenes de la corrida, y da lo mismo que evaluarla contra el
> COCO de su estrato. Una corrida que mezcle estratos y se evalúe contra `bench_v3.json`
> cuenta como falsos positivos las detecciones de `vest` sobre `shel5k` y las de `bare_head`
> sobre `chv` (ver «Qué anota cada fuente y cómo se agrega»). Las cifras publicadas salen de
> cuatro corridas, una por estrato, cada una contra su COCO curado, agregadas con
> `curate/bench_v3_report.py`.

Para CR-01 con GT persona-nivel, usar `curated/person_gt_bench_obra.json` (núcleo, 262
personas / 60 violadores CR-01) o `person_gt_shel5k.json` según qué imágenes procesó el
run — **no existe un person_gt fusionado** (los formatos son compatibles pero el runner ya
restringe por basename del run, así que evaluar cada fuente por separado y sumar
violadores/detectados es más trazable que fusionar de antemano).

> ✎ **2026-08-28 — GT de CR-02 (Nivel A) que esta sección no citaba (`docs/operacion/130`, R-22).**
> Los resultados CR-02 de Nivel A salen de **`curated/person_gt_bench_obra_v2.json`** — GT
> persona-nivel de `bench_obra` con `has_vest` derivado de los **negativos explícitos** del
> núcleo (**142 violadores CR-02**), no de `person_gt_bench_obra.json` (que trae
> `has_vest=True` para todos y sólo sirve para CR-01). CR-02 sólo existe en `bench_obra`:
> `chv` no tiene negativos explícitos y `person_gt_shel5k.json` no anota `has_vest`.

> **PROHIBIDO para evaluación: `processed/coco/bench/person_gt.json` (18-jun) es
> HISTÓRICO.** Se construyó sobre el BENCH contaminado de 196 imágenes: 46 de sus 111
> violadores CR-01 (41%) viven en las 49 imágenes que la curación del 23-jul excluyó
> (selfies COVID, PASCAL VOC, …) — usarlo reintroduce la inflación ≈2× del recall CR-01
> que la curación corrigió. El GT vigente del núcleo es
> `curated/person_gt_bench_obra.json`, regenerable con:
>
> ```bash
> python3 datasets/scripts/bench/build_person_gt.py \
>   --coco datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_val.json \
>          datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_test.json \
>   --out datasets/processed/coco/bench/curated/person_gt_bench_obra.json
> ```
>
> (60 y no 65 violadores: además de las 49 imágenes, la curación removió 4 `bare_head`
> sub-pixel en 2 imágenes conservadas — `curation_bench_obra.md` §2; verificado en
> `datasets/tests/test_person_gt_bench_obra.py`.)
