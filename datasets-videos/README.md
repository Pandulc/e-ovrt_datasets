# Laboratorio de Ground Truth en Video (`datasets-videos/`)

Flujo de adquisición de anotaciones temporales en video mediante CVAT. GT de
salida: **`clip_gt.v2`** (episodios de violación CR-01/CR-02 en milisegundos —
no frame-level, no COCO). Spec completo:
`docs/_archive/superpowers/specs/2026-07-11-video-gt-lab-design.md`.

## Estructura

- `raw/` — videos fuente (cualquier formato/fps/codec)
- `clips/` — videos normalizados a CFR 30fps sin audio + `<clip_id>.info.json`
- `preann/` — pre-anotaciones de media-plane (GDINO-base) + preview MP4, descartables
- `corrected/` — anotaciones CVAT corregidas (CVAT XML 1.1, staging)
- `gt/` — `clip_gt.v2` derivado (episodios en ms)
- `<clip_id>.clip.yaml` — **la ficha de cada clip, en la raíz de este directorio**

### Los `.clip.yaml` viven en la raíz, y no es negociable

Están sueltos acá y no en un subdirectorio porque **dos consumidores los buscan
exactamente en esta ruta**:

| Consumidor | Cómo los busca |
|---|---|
| `datasets/scripts/bench/promote_clip.py` | `<lab>/<clip_id>.clip.yaml`, y está en su lista de archivos **obligatorios** |
| Consola web (`webconsole/backend/.../clips/`) | `videos_dir.glob("*.clip.yaml")`, **no recursivo**; y escribe los nuevos en esta misma raíz |

Moverlos a una carpeta rompe la promoción al banco y la vista de Clips de la
consola. Si alguna vez hay que reorganizarlos, hay que tocar los dos repos y sus
tests a la vez.

### Qué contiene la ficha y para qué sirve cada campo

```yaml
clip_id: v01_c01      # identidad del clip
block: B              # A = rodaje propio guionado | B = obra real
scenario: P5          # caso del shot-list (doc 59)
source_id: v01_c01    # CLAVE DE MATCHEO — ver abajo
level: scene          # scene | subject: cómo se agrupan los episodios
master: raw/1.1.mp4   # de qué video salió (clave extra, la usa la consola)
```

`derive_clip_gt.py` **exige solo `clip_id`, `block` y `scenario`**; el resto tiene
default y las claves extra (`master`, `episode_draft`) se toleran y no se filtran
al GT. Sin esta ficha el script no corre, por más que la anotación de CVAT esté
perfecta.

**El campo que carga el peso es `source_id`.** Es la clave con la que el evaluador
cruza las alertas contra el GT: hace `alert.source_id == episode.source_id`. Si no
coincide, ninguna alerta matchea con ningún episodio — todas cuentan como falsos
positivos y todos los episodios como perdidos. Los resultados salen catastróficos y
la causa es un string. La corrida del bench configura su fuente con este valor
(`ingest.config.source_id`).

Los demás campos son para poder **leer** los resultados después: `block` separa
material real de guionado, `scenario` deja decir "los P2 fallan" en vez de mirar un
promedio ciego, y `level` define si los episodios se agrupan por escena o por
persona. Todo eso se copia dentro del `clip_gt.v2`, así que un archivo de GT se
explica solo meses después.

### Lote de internet: el clip ES el master, sin recortar

Los 14 clips `v01_c01`…`v10_c01` vienen del lote de internet (doc 58 §B.2.1) y
**no se recortan** (doc 59 §6): se usan enteros como material soak para medir FAR.
Recortarlos solo tiraría tiempo negativo, que es justo lo que hay que acumular.
Por eso sus fichas dicen `NO regenerar desde la consola`: la herramienta de recorte
es para el material del rodaje propio, donde se filman 33 s a propósito para
extraer los 20 buenos.

Trece son de cumplimiento (`scenario: P5`) y el GT los marcará `negative: true` solo
con que la corrección en CVAT no deje ningún episodio. El único con una infracción
real es **`v04_c01`** (`scenario: P8`): CR-01 espontáneo nocturno, con el evento a
t≈6 s — ya por encima de los 3,5 s de pre-roll que exige medir el TTFD, así que
tampoco necesita re-ventaneo.

## Pipeline

### Etapa 0 — Normalización (`prepare_clip.sh`)

```bash
datasets/scripts/videogt/prepare_clip.sh <input_video> <clip_id> [--ss T] [--to T] [--fps N] [--scale WxH]
```

Recorta, re-encodea a CFR (fps entero, default 30) sin audio y calcula el
sha256. `clip_id` solo admite `[A-Za-z0-9_-]`. Emite `clips/<clip_id>.mp4` +
`clips/<clip_id>.info.json`. Todo lo que entra a CVAT pasa por acá — nunca se
anota sobre el video fuente.

### Etapa 1 — Pre-anotación (media-plane, ya implementada)

```bash
cd ../e-ovrt_media-plane
python -m eovrt_media.tools.preannotate_video <clip_id>.mp4 \
  --out <clip_id>.xml [--preview] [--sample-fps 10] [--device cuda]
```

GDINO-base + ByteTrack sobre cajas de persona, con `has_helmet`/`has_vest`
inicializados por asociación espacial. Emite CVAT for video 1.1.

### Etapa 2 — Corrección humana en CVAT

1. Crear task en CVAT con `clips/<clip_id>.mp4` y cargar la config de labels
   de `datasets/scripts/videogt/cvat_labels.json` (label `person`; atributos
   `has_helmet`/`has_vest` tipo radio, valores `unknown`/`true`/`false`,
   default `unknown` — un checkbox sin tocar NUNCA debe fabricar una
   violación).
2. **Upload annotations** del XML de pre-anotación ("CVAT for video 1.1"). No
   hay job de "Ground Truth" ni formato JSONL de por medio.
3. Corregir bboxes/tracks y resolver cada atributo (`unknown` → `true`/`false`
   según lo visto) siguiendo el protocolo §5 del spec.
4. Exportar como **CVAT for video 1.1** → guardar en `corrected/<clip_id>.xml`.

### Etapa 3 — Derivación

Requiere además `<clip_id>.clip.yaml` con metadata no inferible del video
(`clip_id`, `block`, `scenario`, `level`, `recording`, `annotation` — §4.2, y
opcionalmente `source_id` si la fuente del bench no coincide con el `clip_id`).

```bash
python3 datasets/scripts/videogt/derive_clip_gt.py \
  --xml corrected/<clip_id>.xml --clip-yaml <clip_id>.clip.yaml \
  --info clips/<clip_id>.info.json --out gt/<clip_id>.json \
  [--pattern-set "CR-01=4000,CR-02=7000"] [--allow-empty]
```

El default del `--pattern-set` (CR-01=4000, CR-02=7000 ms) está alineado con el
pattern set oficial del motor (`cr01_cr02_v2`, Tabla D.4). Si la corrida usa otro
pattern set, pasá el mismo acá: productor y evaluador deben clasificar
episodio/sub-umbral con los MISMOS umbrales (el GT graba los suyos en
`provenance.pattern_set_ms` y el evaluador los usa).

Emite `clip_gt.v2` (episodios, `sub_threshold_events`, bloque `provenance`
con el sha256 del XML) + timeline en consola para la revisión final humana.
Todo episodio lleva `source_id` (identidad de escena para el evaluador del
control-plane — default `clip_id`, override con `source_id` en clip.yaml);
los episodios `level: subject` llevan además `subject_key` (= `subject_label`,
clave LOCAL al clip, sin mapeo al motor de alertas — ver §4.3 del spec).
`--allow-empty` es solo para un negativo intencional (sin personas en
cuadro); por default, un XML sin tracks `person` hace fallar la derivación en
vez de emitir un negativo silencioso.

### Etapa 4 — Validación y doble anotación

```bash
python3 datasets/scripts/bench/validate_clip_gt.py \
  --gt-dir gt/ [--manifest <manifest.yaml> --base-dir <dir>]
python3 datasets/scripts/videogt/compare_annotations.py \
  --a gt/<clip_id>_a.json --b gt/<clip_id>_b.json
```

`validate_clip_gt.py` valida schema, `level`, `subjects_in_evidence`,
episodios dentro de `duration_ms`, sin solape de la misma condición,
`negative` ⇔ sin episodios, y (con `--manifest`) manifest ↔ archivos ↔
sha256. `compare_annotations.py` compara dos derivaciones independientes
(doble anotación) y computa kappa de Cohen + |Δstart|/|Δend| medianos.

### Etapa 5 — Promoción al banco

```bash
python3 datasets/scripts/bench/promote_clip.py --clip-id <clip_id> \
  [--lab-dir datasets-videos] [--state preannotated|corrected|gt_ready]
```

Copia los artefactos del laboratorio (`clips/<id>.mp4`, `clips/<id>.info.json`,
`<id>.clip.yaml`, `preann/<id>.xml` — obligatorios — y `corrected/<id>.xml`,
`gt/<id>.json` si ya existen) al layout del banco, **verificando el sha256
del `.mp4` contra `info.json` antes de copiar nada**. Deriva el `state`
automáticamente de qué artefactos existen (`preannotated` → `corrected` →
`gt_ready`, este último solo si el GT pasa `validate_gt`); `--state` fuerza
un valor explícito. El upsert en `manifest.yaml` es idempotente por
`clip_id`: re-promover el mismo clip actualiza la fila (no la duplica) y
reordena todo por `clip_id`.

Layout del banco (`datasets/processed/clip_bench/` + `datasets/raw/clip_bench/`):

```
datasets/raw/clip_bench/clips/<clip_id>.mp4        # GIT-IGNORED (sube a Drive a mano)
datasets/processed/clip_bench/
├── manifest.yaml                                   # índice del banco (clip_id, file, sha256, state, ...)
├── meta/<clip_id>.clip.yaml                        # metadata (copia de la del laboratorio)
├── meta/<clip_id>.info.json                        # sha256/fps/n_frames/resolution del clip preparado
├── preann/<clip_id>.xml                            # pre-anotación (la que se importa en CVAT)
├── annotations/<clip_id>.xml                       # XML corregido exportado de CVAT (si existe)
└── gt/<clip_id>.json                               # clip_gt.v2 (si existe)
```

**Política de versionado:** el `.mp4` NO se commitea (va a Drive manualmente;
`datasets/raw/clip_bench/` queda git-ignored por la regla `*.mp4` general de
`.gitignore`). TODO lo demás del banco (`manifest.yaml`, `meta/`, `preann/`,
`annotations/`, `gt/`) se commitea — quien clona el repo en la PC de CVAT
tiene todo menos el video, que baja de Drive y verifica por sha256 contra
`manifest.yaml`.

Para validar el manifest resultante (schema del GT si existe + cruce
`manifest ↔ archivos ↔ sha256`):

```bash
python3 datasets/scripts/bench/validate_clip_gt.py \
  --manifest datasets/processed/clip_bench/manifest.yaml \
  --base-dir datasets/processed/clip_bench
```

Una fila con `state` distinto de `gt_ready` (clip recién promovido, todavía
sin pasar por CVAT/derivación) no exige `gt`; una fila `gt_ready` sí lo exige.

## Spec completo

Ver `docs/_archive/superpowers/specs/2026-07-11-video-gt-lab-design.md`: pipeline
(§3), formatos y contratos (§4), protocolo de corrección en CVAT (§5), layout
y dependencias (§6).
