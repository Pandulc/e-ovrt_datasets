# Registry — `clip_bench` (banco de clips con GT temporal)

Análogo de [`bench_v3.md`](bench_v3.md) para **video**. El bench de imágenes mide
percepción (mAP, AP@0.5); este banco mide **patrones de riesgo con GT temporal**:
precision/recall de episodios, `t_alert-system`, TTFD y SDR.

- **Estado:** `reportable` (los 34 clips en `gt_ready`) — 2026-08-03
- **Manifest:** `datasets/processed/clip_bench/clip_bench_manifest.json`
  (`schema_version: clip_bench_manifest.v1`)
- **`manifest.yaml` sha256:** `cef5082e1eb1981c89251ba1b45d7ff044627f8aa1e428f50e0601abe64260e8`
- **Checksums:** `clip_bench.sha256` — verificar con
  `cd datasets/processed/clip_bench && sha256sum -c clip_bench.sha256`

## 1. Composición

| | |
|---|---|
| Clips | **34**, todos con GT, todos `gt_ready` |
| Bloque | A (rodaje guionado 2026-07-25) — 34/34 |
| Escenarios | P1:11 P2:5 P3:2 P4:2 P5:2 P6:2 P7:4 P8:1 P9:5 — **P1–P9 sin huecos** |
| Positivos / negativos / soak | 30 / 4 / **0** |
| Episodios | **35** — CR-01: 28, CR-02: 7 |
| Duración total | 1.072.736 ms (**17 min 53 s**) |
| Duración negativa | 128.834 ms (0,0358 h) |
| Denominador FAR/hora | **0,0 h** (solo clips soak, doc 57 §3.2 G1) |

## 2. Procedencia

1. **Rodaje** 2026-07-25, Bloque A, guionado (doc 69 = guion operativo; fichas por
   clip en `datasets-videos/docs/ficha-eventos-rodaje.md`). Fuentes: OAK-D PoE y DVR.
   Consentimientos de los participantes: administrativo del rodaje.
2. **Etapa 0** — `prepare_clip.sh`: normalización a CFR sin audio + `.info.json`
   (fps entero, `n_frames`, sha256). Sin esto el mapeo frame↔ms no es exacto.
3. **Pre-anotación** — `preannotate_video` (GDINO-**base**, más fuerte que el tiny
   evaluado: anti-circularidad) + ByteTrack.
4. **Corrección humana en CVAT** — proyecto `TFG`, equipo del usuario. **El export
   fue a nivel PROYECTO**, que numera los frames en un espacio global y continuo;
   se dividió con `split_cvat_project.py` (rebase de frames + `<meta><task><size>`
   para reactivar el guard I2). Sin ese paso el GT sale **negativo en silencio**
   (doc 80 §2).
5. **Adjudicación de huecos `unknown`** — 6 clips, ver limitación L3.
6. **Derivación** — `derive_clip_gt.py`, pattern set **`cr01_cr02_v2`**
   (CR-01 4000 ms / CR-02 7000 ms). Nunca v1: produce falsos `missed`.
7. **Promoción y ensamblado** — `promote_clip.py` (estado derivado de los
   artefactos reales, nunca impuesto) + `build_clip_bench.py`.

## 3. Limitaciones declaradas

Se declaran acá **antes** de reportar resultados, no se descubren después.

### L1 — FAR/hora no es una métrica reportable de este trabajo (determinación 2026-08-04)

El denominador de FAR/hora exige negativos de ≥5 min (doc 57 §3.2, gate G1). El
banco no tiene ninguno: los 4 negativos suman 0,0358 h y **no entran al
denominador** (el manifest lo declara explícito en `far_denominator_basis`).

**Determinación (doc 90 D-90.1 del repo `docs`):** no se trata de un pendiente sino de
un límite del material. Con 0 FP y la regla de 3 hacen falta **3,0 h** de video en
cumplimiento anotado para poder afirmar "FAR ≤ 1 FA/hora" (umbral **ilustrativo**: el
proyecto no pre-registró un objetivo de FAR — el punto es que ninguna cota alcanzable
sostiene una afirmación); el banco alcanza **0,10 h** con el clip soak previsto
(6,2 min del lote de internet) y como mucho **0,26 h** si se agregaran todos los
negativos cortos (tiempos efectivos, descontando 7 s de warm-up por clip: nadie puede
alertar antes de la persistencia). Una cota de 11–30 falsas alarmas por hora no
sostiene ninguna afirmación operativa, así que **reportar FAR/hora como métrica de
rendimiento sería reportar ruido**. La mecánica pre-registrada no cambia: el agregador
ya emite `far_per_hour: null` sin soak, con la base declarada.

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

### L4 — Un solo bloque, material guionado

Los 34 clips son Bloque A: **rodaje guionado**, un escenario controlado, mismos
actores y locación. No hay obra real. La generalización a obra real **no está
medida por este banco** — el bench de imágenes `bench_v3` sí cubre 3 fuentes
independientes, y el lote de internet aportará video no guionado.

El clip de obra real que existía (`cb_b01_p7`) fue **retirado** el 2026-08-03:
licencia/consentimiento sin registrar y GT producido por IA. Motivo completo en
`datasets/processed/clip_bench/_retired/cb_b01_p7/MOTIVO.md`.

### L5 — Escenarios desbalanceados

P1 aporta 11 clips y P8 solo 1. Los agregados por condición están dominados por
P1/P2 (16 de 34). **Reportar por escenario además del agregado**, igual que la
regla de `bench_v3` para estratos.

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

Determinista: mismo export + mismos `clip.yaml` → mismo `manifest.yaml` sha256.
