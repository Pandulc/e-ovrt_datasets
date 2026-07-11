# Spec — Laboratorio de GT de video (`video-gt-lab`)

- **Fecha:** 2026-07-11
- **Estado:** **Implementado y verificado (2026-07-11).** 11 tasks ejecutadas con
  subagent-driven-development; suites en verde (datasets 70 tests, media-plane 503).
  El pipeline corrió end-to-end sobre `recorte-1.mp4` (obra real, ~10 operarios, GPU).
  Una revisión final de rama halló 3 defectos críticos + 5 importantes, todos
  corregidos y re-verificados. **Este documento fue reconciliado con el
  as-built**: las secciones marcadas *(corregido en implementación)* difieren del
  diseño original porque la revisión encontró que la propuesta inicial rompía una
  invariante o no funcionaba. **Pendiente:** el roundtrip real en CVAT (etapa 2,
  §7) requiere una máquina con CVAT y no se ejecutó todavía. Nada commiteado.
- **Repo dueño:** `e-ovrt_datasets` (derivación, validación, layout). Un componente
  vive en `e-ovrt_media-plane` (pre-anotación, por entorno GPU e infra de modelos).
- **Relación con el spec 43 (`docs/specs/43-clip-bench-gt-temporal.md`):** este spec
  **implementa el tooling** con el que se ejecuta el spec 43. No redefine el formato
  `clip_gt.v2`, ni la composición del banco, ni las métricas — todo eso queda como
  está en el 43. Lo que agrega es el **cómo**: pipeline semi-automático de anotación
  (pre-anotación con modelo fuerte → corrección humana en CVAT → derivación
  determinística de episodios) en lugar de anotación puramente manual de timestamps.
- **Área de trabajo:** `e-ovrt_datasets/datasets-videos/` (laboratorio). El banco
  final va al layout del spec 43 §5 (`datasets/raw/clip_bench/`,
  `datasets/processed/clip_bench/`).

## 1. Objetivo

Producir GT temporal `clip_gt.v2` para clips de video de forma **rápida, objetiva y
defendible**, reemplazando la anotación manual de timestamps "a ojo" por:

1. bboxes de persona por frame con **atributos temporales** `has_helmet`/`has_vest`,
   pre-anotadas por un modelo **más fuerte que el evaluado** y corregidas por un
   humano en CVAT;
2. **derivación determinística** de episodios CR-01/CR-02 desde los timelines de
   atributos (script, no juicio humano sobre timestamps).

### 1.1 Argumento de defensa que este diseño compra

- **Anti-circularidad:** el GT lo produce GDINO-**base** (SwinB) — estrictamente más
  capaz que el GDINO-tiny evaluado — más corrección humana. El sistema bajo prueba
  no participa en la generación de su propio GT.
- **Anti-anclaje:** la pre-anotación de cajas de persona es orientada a recall
  (el humano borra/ajusta, que resiste mejor el sesgo de anclaje que agregar), y el
  protocolo obliga a verificar cada transición de atributo contra el video.
- **Bordes objetivos:** `start_ms`/`end_ms` salen de un cálculo sobre estados por
  frame corregidos, no de "cuándo me parece que empezó". La resolución es de frame
  (33 ms a 30 fps), muy por debajo de la tolerancia de ±500 ms del spec 43 §4.2.

## 2. Decisiones de diseño (cerradas en brainstorming)

| # | Decisión | Elección | Alternativas descartadas |
|---|---|---|---|
| D1 | Nivel de GT | Bboxes de persona + atributos → **derivar** episodios `clip_gt.v2` | Solo episodios asistidos (corrección subjetiva de timestamps); solo bboxes (no cierra spec 43) |
| D2 | Motor de pre-anotación | GDINO-base (HF `IDEA-Research/grounding-dino-base`) + tracking, offline | Mismo stack tiny (circularidad); híbrido tiny+recall (argumento menos limpio) |
| D3 | Herramienta de corrección | **CVAT** (tracks nativos, interpolación, merge/split; corre en otra PC) | Label Studio imágenes a 5 fps (UX madura pero sin tracks); LS video (inmaduro) |
| D4 | Esquema de anotación | Track `person` con atributos temporales `has_helmet`/`has_vest` | 4 clases canonical_v2 en video (3-4× esfuerzo + asociación frágil); híbrido con cajas "silver" |

**Consecuencia de D4:** no se produce GT de cajas de casco/chaleco en video. Está
alineado con el spec 43 ("fuera de alcance: anotación de bboxes por frame" para
detección — la detección se evalúa en BENCH v2 sobre imágenes).

## 3. Pipeline

```
video fuente ─▶ [0 prepare] ─▶ clip CFR ─▶ [1 preannotate] ─▶ CVAT XML + preview
 (datasets-      ffmpeg          .mp4        (media-plane,        │
  videos/raw/)   CFR+recorte              GDINO-base+track)       ▼
                                                        [2 CVAT: corrección humana]
                                                          (otra PC, protocolo §5)
                                                                  │ XML corregido
                                                                  ▼
manifest.yaml ◀─ [4 validate] ◀─ clip_gt.v2 ◀─ [3 derive] ◀─ XML + clip.yaml
+ registry        validate_clip_gt.py            derive_clip_gt.py
```

Cada etapa es un artefacto en disco — el pipeline es re-ejecutable por partes y
cada transformación es inspeccionable.

### 3.0 Etapa 0 — `prepare_clip.sh` (repo datasets, bash + ffmpeg)

Los videos de origen (celular) suelen ser **VFR** (frame rate variable), lo que
rompe el mapeo frame↔ms entre pre-anotación, CVAT y derivación. Este paso lo
elimina por construcción.

- **Input:** video fuente + `clip_id` + (opcional) `-ss`/`-to` de recorte.
- **Hace:** recorte, re-encode a **CFR** (fps declarado, default 30), **sin pista de
  audio**, resolución objetivo si se pide (Tabla C.2: 1280×720 base), y calcula
  **sha256** del resultado.
- **Output:** `datasets-videos/clips/<clip_id>.mp4` + línea para `manifest.yaml`
  (clip_id, sha256, fps, duración, resolución).
- **Regla:** TODO lo que entra a CVAT y a la derivación es un clip preparado por
  esta etapa. Nunca se anota sobre el video fuente.

### 3.1 Etapa 1 — `preannotate_video` (repo media-plane, `eovrt_media.tools.*`)

Vive en media-plane porque ahí están el entorno GPU, la infra de carga de modelos
HF y el patrón `tools.*`; el repo datasets se mantiene stdlib+Pillow(+PyYAML).

- **CLI:** `python -m eovrt_media.tools.preannotate_video <clip.mp4>
  --out <clip_id>.xml [--preview] [--sample-fps 10] [--device cuda]`
- **Modelo:** GDINO-base (`IDEA-Research/grounding-dino-base`, descarga directa de
  HF hub). Offline — la latencia no importa.
- **Detección** a `--sample-fps` (default 10) con prompts `person`, `helmet`,
  `safety vest`. **Política de doble umbral:**
  - `person`: umbral **bajo** (default `--person-threshold 0.15`, orientado a
    recall — el humano borra, no agrega). *(corregido en implementación:* ByteTrack
    fija internamente `det_thresh = track_activation_threshold + 0.1` y **ese** es
    el umbral real de nacimiento de track, no el nominal; el código cablea
    `track_activation_threshold = person_threshold − 0.1` para que `--person-threshold`
    sea efectivo. Sin esto, el umbral quedaba clavado en ~0.35 y bajar el flag no
    tenía efecto — un operario lejano detectado a 0.30 nunca aparecía.*)*
  - `helmet`/`vest`: umbral **moderado** (`--ppe-threshold 0.35`).
- **Spans no matcheados:** si GDINO devuelve un span que no matchea ninguna de las
  3 clases, se **cuenta y se advierte** al terminar la corrida (no se descarta en
  silencio): un span de EPP perdido sistemáticamente sesga `has_helmet`/`has_vest`
  a `false` sin señal visual. *(agregado en implementación.)*
- **Asociación EPP→persona (1:1, corregido en implementación):** cada caja de
  casco/chaleco se asigna a lo sumo a **una** persona (mejor contención en la
  región cabeza/torso, desempate por distancia). *El diseño original usaba
  `any()` por persona — un solo casco marcaba `has_helmet=true` a todas las
  personas cuya cabeza lo contuviera, escondiendo la infracción del que no lo
  tenía justo en los cruces multi-persona (P7), y correlacionando el error con el
  sistema evaluado (que hace matching 1:1). Ver `assign_ppe_to_persons`.*
- **Tracking:** ByteTrack (lib `supervision`, **dependencia nueva** de media-plane,
  extra `dev`) sobre las cajas de persona → tracks con id estable.
- **Suavizado temporal de atributos:** voto por mayoría en ventana ~1 s para matar
  el parpadeo del detector (el humano corrige transiciones reales, no ruido).
- **Adelgazamiento de keyframes:** detectar a 10 fps produce un keyframe cada 3
  frames — ingobernable para editar. Se emite keyframe **solo** cuando la caja se
  desvía de la interpolación lineal más de un ε (px) **o** cuando cambia un
  atributo. CVAT interpola el resto.
- **Output:** XML formato **CVAT for video 1.1** — un `<track label="person">` por
  persona, cajas con frames del clip CFR, atributos mutables por keyframe — y,
  con `--preview`, un MP4 con overlay (cajas + id + estado EPP) para inspección
  rápida antes de subir a CVAT. *(implementación:* el preview se transcodifica a
  **H.264** con ffmpeg; OpenCV en este entorno solo produce `mp4v`, que los
  reproductores embebidos en editores/navegadores no abren. Si ffmpeg falta, queda
  en `mp4v` y avisa.*)*

### 3.2 Etapa 2 — Corrección humana en CVAT (protocolo en §5)

- Proyecto CVAT con label `person` (tipo track) y atributos **mutables**
  `has_helmet`, `has_vest`. La configuración de labels se commitea como
  `datasets/scripts/videogt/cvat_labels.json` para que el setup sea reproducible.
- **Tipo de atributo: `radio` con valores `unknown` / `true` / `false`, default
  `unknown` (corregido en implementación).** *El diseño original usaba `checkbox`
  con default `false`. Eso rompía la invariante central en la frontera con CVAT:
  si el anotador dibuja un track y no toca el atributo, CVAT lo exporta como
  `false` = "sin casco", fabricando una infracción sobre una persona que sí
  llevaba EPP. Con `unknown` por default, un atributo no confirmado se lee como
  `None` (el parser mapea solo `true`/`false`), y `None` corta la corrida en la
  derivación — nunca fabrica una infracción a partir de incertidumbre.*
- Flujo: crear task con el clip CFR → importar el XML de pre-anotación
  ("upload annotations", formato CVAT for video 1.1) → corregir → exportar el
  mismo formato.
- CVAT trata los atributos mutables como **función escalón** (mantienen valor
  hasta el próximo keyframe que los cambie) — exactamente la semántica que la
  derivación necesita.

### 3.3 Etapa 3 — `derive_clip_gt.py` (repo datasets, stdlib + PyYAML)

- **Input:** XML corregido + `clip.yaml` (metadata por clip que no se puede
  inferir del video — ver §4.2) + parámetros del pattern set.
- **Reglas de derivación:**
  1. Por track: timeline de atributos → intervalos de condición
     (`has_helmet=false` sostenido → candidato CR-01; `has_vest=false` → CR-02).
  2. `outside=true` **corta** el intervalo (semántica P8: salir de cuadro cierra
     el episodio; espec. 43 §4.1 "fin observable"). Frames `occluded` NO cortan.
  3. Si la condición sigue viva al final del clip, `end_ms = duration_ms` y se
     deja constancia en `notes`.
  4. **Nivel escena (default, G0) — umbralar por track ANTES de fusionar
     (corregido en implementación):** primero se aplica la persistencia mínima a
     cada intervalo **por track**; solo los que sobreviven se **fusionan** en
     episodios de escena (`subjects_in_evidence` = máximo de sujetos concurrentes;
     el validador exige "sin solape de la misma condición"). *El diseño original
     fusionaba primero y umbralaba después: dos personas sin casco 2,5 s cada una,
     solapadas, se unían en un episodio de 4,5 s que ningún sujeto sostuvo — pero
     el motor del control-plane es 1:1 por sujeto y no alertaría, así que ese
     episodio fabricado se contaría como `missed` y subestimaría el recall de
     CR-01, la métrica titular.* Los intervalos por track que no llegan a
     persistencia van a `sub_threshold_events` con su `track_id`.
  5. **Clips P7 (`level: subject`):** sin fusión — un episodio por track, con
     `subject_label` (`persona_A`, `persona_B`, …, y para >26 tracks
     `persona_AA`, `persona_AB`, … estilo hoja de cálculo — corregido en
     implementación tras el smoke con 41 tracks). Los `sub_threshold_events`
     también llevan `subject_label`.
  6. Intervalos con duración **≥ persistencia mínima** del pattern set (parámetro
     CLI `--pattern-set`, default `CR-01=3000,CR-02=5000` ms — nunca hardcodeado)
     → `episodes[]`; menores → `sub_threshold_events[]` con `reason`.
     **Atención:** este default (3 s / 5 s) es un piso técnico, no el operativo del
     banco. El spec 43 §3 pide P1 = "≥ 8 s continuos" y la Tabla D.4 fija PR-01 y
     PR-02 por severidad — al derivar los clips del banco se pasa el `--pattern-set`
     que corresponda a la corrida, no el default.
  7. Conversión frame→ms: `round(frame * 1000 / fps)` sobre el clip CFR.
  8. **Guardas duras (agregadas en implementación)** — `derive_clip_gt.py`
     **falla** (no produce GT silencioso) si: el XML no tiene ningún track
     `person` (salvo `--allow-empty`, para el negativo intencional) — cubre el
     export en formato equivocado o el label mal capitalizado; o si el `<size>`
     del XML difiere de `n_frames` del clip en > 1 frame (el XML corresponde a
     otro video). El GT emitido incluye un bloque `provenance`
     (`xml_sha256`, `pattern_set_ms`, `tool`) para auditar el determinismo.
- **Output:** `clip_gt.v2` JSON (schema del spec 43 §4, sin cambios) + **timeline
  legible en consola** (por track y por condición) para la revisión final humana
  contra el video — la "regla de oro" del spec 43 §3.3 se conserva: el GT sale del
  video; el script solo hace la aritmética.

### 3.4 Etapa 4 — Validación y calidad (repo datasets)

- **`datasets/scripts/bench/validate_clip_gt.py`** — el script que el spec 43 §5 ya
  define (schema v2, episodios dentro de `duration_ms`, sin solape de la misma
  condición, `negative` ⇔ sin episodios, cruce `manifest.yaml` ↔ archivos ↔
  sha256). Tests sobre fixtures sintéticos, sin media real.
- **`datasets/scripts/videogt/compare_annotations.py`** — doble anotación
  (spec 43 §4.2): toma **dos `clip_gt.v2` derivados** del mismo clip (dos
  anotadores corrigen la misma pre-anotación de forma independiente, cada uno
  exporta su XML, cada XML se deriva) y computa **kappa de Cohen** sobre
  presencia/condición por ventana de 1 s + |Δstart| y |Δend| medianos por episodio
  apareado. Salida lista para el reporte consolidado (ADR-006).

## 4. Formatos y contratos

### 4.1 CVAT for video 1.1 (contrato de las etapas 1→2→3)

Se usa el formato nativo de CVAT sin extensiones. Lo que el pipeline exige:

- tracks con `label="person"`;
- cajas `<box frame=.. xtl=.. ytl=.. xbr=.. ybr=.. outside=.. occluded=..
  keyframe=..>`;
- atributos mutables `<attribute name="has_helmet|has_vest">true|false</attribute>`
  dentro de cada caja keyframe. **Un atributo con valor `unknown` (o ausente) se
  lee como `None` = no evaluable, y nunca fabrica infracción** (ver §3.2). El
  writer del media-plane omite los atributos `None` en vez de escribir `false`,
  cerrando la invariante de punta a punta (verificado en el roundtrip
  writer→parser entre repos).

Los XML **corregidos** se commitean (son chicos) en
`datasets/processed/clip_bench/annotations/<clip_id>.xml` — hacen la derivación
del GT reproducible byte a byte. Los XML de pre-anotación son descartables
(regenerables); quedan en el área de laboratorio.

### 4.2 `clip.yaml` (metadata por clip, input de la derivación)

Lo que el spec 43 pide y no se puede inferir del video:

```yaml
clip_id: cb_a01_p1_cr01
block: A            # A | B | C
scenario: P1        # P1..P8 | V1..V3
level: scene        # scene | subject (subject solo P7)
# source_id: custom_source   # opcional; default = clip_id. El matching de
#   escena del evaluador (control-plane) es `alert.source_id ==
#   episode.source_id`, y la corrida del bench configura su fuente con el
#   clip_id — este override existe solo para el caso en que la fuente real
#   del bench no coincida 1:1 con el clip_id.
recording:
  resolution: 1280x720
  distance_band_m: "5-10"
  lighting: natural
  occlusion: low
annotation:
  annotator: a1
  double_annotated: false
```

`fps_nominal`, `duration_ms` y `source_file` los completa la derivación desde el
clip preparado y el manifest (una sola fuente de verdad, sin duplicación manual).

### 4.3 `clip_gt.v2`

Respeta el schema del spec 43 §4; este spec no lo redefine. **Extensiones
aditivas (implementación):**

- Un bloque `provenance` con `xml_sha256`, `pattern_set_ms` y `tool`, para poder
  auditar que re-derivar produce el mismo GT y de qué XML/parámetros salió.
- **Identidad de los episodios**, exigida por el evaluador del control-plane
  (`evaluation/temporal.py`, `ClipEpisodeV2`): TODO episodio lleva `source_id`
  (convención `source_id = clip_id`, override opcional en clip.yaml — ver
  §4.2), porque el matching de escena del evaluador es
  `alert.source_id == episode.source_id`. Los episodios `level: subject`
  llevan ADEMÁS `subject_key` = `subject_label` — una clave LOCAL a ese clip
  derivada de los tracks de CVAT (`persona_A`, `persona_B`, …) que NO mapea a
  las claves `{pattern}:{source}:{track}` del motor de alertas en vivo, por lo
  que el matching automático por sujeto individual no es posible con este GT.
  Los clips P7 con `level: subject` son para comparación cualitativa G0/G1;
  para métricas (recall/precision) esos episodios se derivan a nivel scene.

El validador acepta el campo extra `provenance` sin rechazarlo.
`validate_clip_gt.py` además chequea `level ∈ {scene, subject}`,
`subjects_in_evidence ≥ 1`, que un episodio `scene` no traiga `subject_label`,
que un episodio `scene` traiga `source_id` y uno `subject` traiga
`subject_key` (espejo exacto del contrato del evaluador), la estructura de
`sub_threshold_events`, y **advierte** por cada clip `negative:true` cuyo
`scenario` no sea P5/V3 (posible export vacío encubierto).

## 5. Protocolo de corrección en CVAT (resumen operativo)

1. Mirar el clip entero una vez, sin anotaciones (contexto).
2. **Tracks:** borrar FPs de persona, unir ids fragmentados (merge), separar
   switches (split), ajustar cajas gruesas. Marcar `outside` SOLO en salidas
   reales de cuadro; oclusiones parciales → `occluded`, la caja sigue.
3. **Atributos:** recorrer **cada transición** de `has_helmet`/`has_vest` sugerida
   y verificarla contra el video; buscar transiciones faltantes en los tramos
   largos sin cambios (el suavizado puede haberse comido un evento corto — los
   transitorios P3 importan como `sub_threshold_events`).
4. Exportar y correr `derive_clip_gt.py`; revisar el timeline impreso contra el
   video (última verificación humana). Si algo no cierra, volver a 2.

Presupuesto esperado: **5–10 min por clip de 30 s** con 1–3 personas (contra
30–60 min de anotación manual densa).

## 6. Layout y dependencias

```
e-ovrt_datasets/
├── datasets-videos/                  # LABORATORIO (media git-ignored)
│   ├── raw/                          # videos fuente tal como llegan (recorte-1.mp4 → acá)
│   ├── clips/                        # clips CFR preparados (etapa 0)
│   ├── preann/                       # XML de pre-anotación + previews (descartables)
│   ├── corrected/                    # XML exportados de CVAT (staging)
│   └── gt/                           # clip_gt.v2 drafts (staging)
├── datasets/scripts/videogt/         # NUEVO
│   ├── prepare_clip.sh
│   ├── derive_clip_gt.py
│   ├── compare_annotations.py
│   └── cvat_labels.json
├── datasets/scripts/bench/validate_clip_gt.py   # NUEVO (definido por spec 43)
└── datasets/tests/                   # tests de derive/validate/compare (fixtures sintéticos)

e-ovrt_media-plane/
└── src/eovrt_media/tools/preannotate_video.py   # NUEVO (+ dep `supervision` en extra dev)
```

Banco final (cuando un clip se promueve del laboratorio al banco, vía
**`datasets/scripts/bench/promote_clip.py`** — NUEVO, gap cerrado en la
auditoría 2026-07-11):

```
datasets/raw/clip_bench/clips/<clip_id>.mp4        # GIT-IGNORED (Drive)
datasets/processed/clip_bench/
├── manifest.yaml                                   # COMMIT — índice del banco
├── meta/<clip_id>.clip.yaml                        # COMMIT
├── meta/<clip_id>.info.json                        # COMMIT
├── preann/<clip_id>.xml                            # COMMIT
├── annotations/<clip_id>.xml                       # COMMIT (si existe)
└── gt/<clip_id>.json                               # COMMIT (si existe)
```

**Política de versionado:** el `.mp4` no se commitea (va a Drive a mano; la
regla `*.mp4` de `.gitignore` ya cubre `datasets/raw/clip_bench/clips/`, sin
reglas adicionales). Todo lo demás del banco se commitea — quien clona el
repo en la PC de CVAT tiene XML de pre-anotación, XML corregido, GT, metadata
y manifest, y le falta solo el video (que baja de Drive y verifica por
sha256 contra `manifest.yaml`).

`promote_clip.py --clip-id <id> [--lab-dir datasets-videos] [--state ...]`
copia los artefactos del laboratorio al layout de arriba, verificando el
sha256 del `.mp4` ANTES de copiar, derivando el `state`
(`preannotated`→`corrected`→`gt_ready`) de qué artefactos existen (nunca lo
inventa), y haciendo upsert idempotente de la fila en `manifest.yaml` (no
duplica clips ya promovidos). `validate_clip_gt.py --manifest ... --base-dir
datasets/processed/clip_bench` exige `gt` solo en filas `state: gt_ready` —
una fila recién promovida sin GT todavía no falla la validación.

**Dependencias nuevas:** `supervision` (ByteTrack) en media-plane extra `dev`;
`PyYAML` documentado como requisito de los scripts `videogt/` del repo datasets
(el `manifest.yaml` del spec 43 lo exige de todos modos). ffmpeg/ffprobe como
requisito de sistema para la etapa 0.

## 7. Smoke end-to-end del laboratorio (criterio de terminado de ESTE spec)

Sobre `recorte-1.mp4` (resultó ser obra real en plano general, ~10 operarios —
no un escenificado del Bloque A; sirve como conejillo de indias del pipeline):

- [x] Etapa 0: clip preparado (`lab_recorte1.mp4`, CFR 30 fps, 733 frames) con
      sha256 y `info.json`.
- [x] Etapa 1: XML de pre-anotación con GDINO-base en GPU (7m19s) → 41 tracks,
      1093 keyframes; preview H.264 inspeccionado (detección coherente).
- [ ] **Etapa 2 — PENDIENTE (requiere máquina con CVAT):** importar el XML,
      corregir, re-exportar; verificar el roundtrip (import → export sin editar
      produce el mismo GT). **El XML del writer todavía no pasó por un CVAT real:
      este contrato es lo único sin validar del laboratorio.**
- [x] Etapa 3: `clip_gt.v2` derivado (ensayo en seco sobre el XML de
      pre-anotación, sin corrección humana); timeline y `provenance` presentes.
- [x] Etapa 4: `validate_clip_gt.py` → 0 errores; suites en verde (datasets 70,
      media-plane 503).
- [x] Doble anotación ensayada (`compare_annotations.py` emitió kappa +
      |Δstart|/|Δend| entre dos derivaciones).

La ejecución del **banco completo** (grabación A+C, bloque B, consentimientos,
registry, smoke con evaluate-alerts) queda regida por el spec 43 §8–§9 — este
laboratorio es la herramienta con la que se ejecuta, no la ejecución.

## 8. Fuera de alcance

- GT de cajas de casco/chaleco/bare_head en video (D4; spec 43 lo excluye).
- GT MOT / trayectorias por frame (E-10 sigue "no aplicable", ADR-002).
- Fine-tuning con datos derivados de video.
- Integración runtime con la plataforma (esto es un laboratorio offline).
- Cambios a `clip_gt.v2`, a `evaluate-alerts` (spec 41) o al manifiesto de
  corridas (spec 44).

## 9. Interfaces con otros specs

- **Spec 43:** este spec implementa sus §3.3 (tiempos reales contra video),
  §4 (produce `clip_gt.v2` válido), §4.2 (doble anotación con kappa), §5 (layout,
  `validate_clip_gt.py`, manifest con sha256) y §8 pasos 4–6.
- **Spec 41 (control-plane):** sin cambios — `evaluate-alerts` v2 ya consume
  `clip_gt.v2`.
- **Spec 44 (experimental-setup):** sin cambios — el manifiesto de corrida
  referencia `clip_id` del manifest del banco.
