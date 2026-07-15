# Cómo funciona el etiquetado en CVAT (y cómo lo usamos nosotros)

Este documento explica **a fondo el modelo mental** del etiquetado de video en
CVAT y cómo cada cosa que dibujás se convierte en el ground-truth (GT) del banco.
Es el complemento conceptual de [`../GUIA-CVAT.md`](../GUIA-CVAT.md), que es la
guía operativa paso a paso (levantar el servicio, importar, exportar). Si querés
"qué botón toco", andá a la guía; si querés "por qué esto funciona así", quedate acá.

El diseño completo vive en el spec:
`docs/superpowers/specs/2026-07-11-video-gt-lab-design.md`.

---

## 1. Dónde encaja CVAT en el pipeline

CVAT es **una sola etapa** de un pipeline de 5 etapas. No genera datos de la nada:
corrige lo que un modelo ya pre-anotó.

```
video fuente ─▶ [0 prepare] ─▶ clip CFR ─▶ [1 preannotate] ─▶ CVAT XML + preview
 (raw/)         ffmpeg          .mp4        GDINO + ByteTrack     │
                CFR+recorte                 (máquina GPU)         ▼
                                                        [2 CVAT: corrección humana]  ← ACÁ ESTAMOS
                                                          (esta PC, protocolo §5)
                                                                  │ XML corregido
                                                                  ▼
manifest ◀─ [4 validate] ◀─ clip_gt.v2 ◀─ [3 derive] ◀─ XML + clip.yaml
```

- **Etapa 0** (`prepare_clip.sh`): recorta el video y lo re-encodea a **CFR**
  (constant frame rate, 30 fps). Esto es crítico: los videos de celular son VFR
  (frame rate variable) y eso rompería el mapeo frame↔milisegundo. Todo lo que
  entra a CVAT es un clip preparado por esta etapa, **nunca** el video crudo de `raw/`.
- **Etapa 1** (`preannotate_video`, en la máquina con GPU): corre GroundingDINO +
  ByteTrack sobre el clip y produce el **XML de pre-anotación** (`preann/<clip>.xml`)
  con un track por persona y una estimación de casco/chaleco. Es un borrador
  generoso: el detector prefiere marcar de más (recall alto) porque **el humano borra, no agrega**.
- **Etapa 2 — CVAT (vos)**: importás ese XML, lo corregís contra el video, exportás
  el XML corregido a `corrected/<clip>.xml`.
- **Etapa 3** (`derive_clip_gt.py`): convierte el XML corregido en el GT final
  (`gt/<clip>.json`) haciendo pura aritmética.
- **Etapa 4** (`validate_clip_gt.py`): valida el GT contra el schema.

**La regla de oro:** el GT sale del video que vos mirás y corregís; el script solo
hace las cuentas (frames → milisegundos, intervalos → episodios). Si CVAT queda mal,
el GT queda mal — no hay red de contención después.

---

## 2. El modelo de datos de CVAT

### 2.1 Task y Job

- **Task** = el trabajo sobre un clip. Cuando creás la task subís **un** `.mp4`
  (el de `clips/`) y CVAT lo descompone en frames. Para `cb_b01_p7` son 733 frames
  (0–732), 30 fps, ~24,4 s.
- **Job** = el espacio de anotación real dentro de la task. Con clips cortos hay
  **un solo Job** por task. Todo lo que dibujás vive en el Job.

### 2.2 Frames, no segundos

CVAT trabaja en **frames enteros**, no en tiempo. El frame es la unidad atómica.
La conversión a tiempo la hace después la derivación:

```
ms = round(frame * 1000 / fps)     # con fps = 30
```

Por eso importa tanto el CFR: si el fps fuera variable, `frame * 1000 / fps` daría
un tiempo equivocado. La derivación incluso **falla a propósito** si el `<size>`
del XML (cantidad de frames) no coincide con el `n_frames` del clip preparado —
es la señal de que la task se creó sobre el video equivocado.

### 2.3 Track vs Shape (la distinción más importante)

CVAT tiene dos formas de anotar un objeto:

| | **Shape** | **Track** |
|---|---|---|
| Qué es | una caja en **un solo frame** | una caja que **vive a lo largo del tiempo** |
| Uso | imágenes sueltas | **video** (lo nuestro) |
| Interpolación | no | **sí** — entre keyframes |

**Nosotros SIEMPRE usamos Track.** Una persona = un track. No dibujás una caja por
frame: dibujás la caja en unos pocos frames clave y CVAT rellena el resto.

Cuando dibujás un objeto nuevo, en la barra superior asegurate de que el modo diga
**Track**, no **Shape**. Si sale como Shape, el objeto existe en un solo frame y la
derivación lo va a ver como una persona que aparece un instante y desaparece.

### 2.4 Keyframes e interpolación

Un track está definido por **keyframes**: frames donde vos fijaste explícitamente
la posición/estado de la caja. Entre dos keyframes, CVAT **interpola linealmente**
la posición de la caja.

```
keyframe f=0            (interpolado)            keyframe f=90
 [caja en x=100] ─────────────────────────────▶ [caja en x=340]
                  en f=45 CVAT dibuja x≈220 solo
```

Práctica: seguís a la persona avanzando frames, y **solo cuando la caja se
desalinea** del cuerpo real, la reacomodás — ese ajuste crea un keyframe ahí.
No hace falta tocar frame por frame. La pre-anotación ya viene con keyframes
"adelgazados" (uno cada tanto, no uno cada 3 frames) justo para que sea editable.

### 2.5 `outside` y `occluded` (los dos flags de visibilidad)

Cada keyframe de un track lleva dos flags que cambian el significado del track:

- **`outside`** = la persona **salió de cuadro de verdad**. Marca el **fin del
  episodio** de esa persona. La caja deja de "contar" desde ese frame. En la UI:
  botón *Outside* / atajo. Marcalo en el frame donde la persona ya no está.
- **`occluded`** = la persona **sigue ahí pero tapada** (una máquina cruza delante,
  otra persona la ocluye). La caja **sigue viva**, solo se marca visualmente como
  ocluida. **No corta** el episodio.

Esta diferencia es sustantiva, no cosmética:

> Oclusión parcial → `occluded`, la caja sigue.
> Salida real de cuadro → `outside`, cierra el episodio.

Si marcás `outside` cuando en realidad era una oclusión, cortás un episodio que
debía seguir. Si dejás la caja viva cuando la persona ya se fue, fabricás un
episodio fantasma. En obra real (P7) con maquinaria cruzando, la mayoría de las
"desapariciones" son **oclusiones**, no salidas.

---

## 3. Nuestro esquema de labels

El esquema se commitea en `datasets/scripts/videogt/cvat_labels.json` para que el
setup sea reproducible. Es un solo label con dos atributos:

```json
[
  {
    "name": "person",
    "type": "rectangle",
    "attributes": [
      {"name": "has_helmet", "mutable": true, "input_type": "radio",
       "default_value": "unknown", "values": ["unknown", "true", "false"]},
      {"name": "has_vest", "mutable": true, "input_type": "radio",
       "default_value": "unknown", "values": ["unknown", "true", "false"]}
    ]
  }
]
```

### 3.1 El label `person`

- Se llama **`person`**, en minúscula, exacto. La derivación busca ese string
  literal; si queda `Person`, `Persona` o cualquier variante, el script **falla**
  (guarda dura — ver §6). No es case-insensitive.
- Es de tipo **rectangle** (caja) y lo usamos como **track**.

### 3.2 Los atributos `has_helmet` y `has_vest`

Cada persona carga dos atributos que describen su **estado de EPP** (equipo de
protección personal) a lo largo del tiempo:

| Atributo | Condición asociada | Pregunta |
|---|---|---|
| `has_helmet` | **CR-01** | ¿tiene el casco puesto? |
| `has_vest` | **CR-02** | ¿tiene el chaleco puesto? |

Cada uno toma tres valores: **`unknown` / `true` / `false`**, con default `unknown`.

Son **`radio`** (no checkbox) y **`mutable`** (pueden cambiar a lo largo del track,
por keyframe). Estas dos propiedades no son casuales: son la protección central del
diseño.

---

## 4. La semántica que hace que todo funcione

### 4.1 Los atributos son función escalón

Un atributo mutable en CVAT es una **función escalón**: el valor que fijás en un
keyframe **se mantiene** hasta el próximo keyframe donde lo cambies. No es "el valor
en ese instante", es "el valor desde acá en adelante".

```
f=0 ── has_helmet=true ──────────────────┐
                                        f=240 ── has_helmet=false ──────────┐
                                                                          f=450 ── has_helmet=true ──── (fin)
```

Lectura: "traía casco; en el frame 240 (~8 s) se lo saca; en el 450 (~15 s) se lo
vuelve a poner". Tres keyframes de atributo describen toda la historia. La derivación
materializa esto frame por frame (`attribute_states` en `cvat_xml.py`).

Práctica: para marcar que alguien se sacó el casco, no tenés que tocar cada frame
del tramo — fijás `false` en el keyframe donde se lo saca y `true` (o el valor que
corresponda) en el keyframe donde se lo vuelve a poner. El medio se rellena solo.

### 4.2 `unknown` NO es lo mismo que `false`

Esta es **la** invariante del laboratorio:

| Valor | Significado | Efecto en el GT |
|---|---|---|
| `true` | estás seguro de que **SÍ** lleva el EPP | cumplimiento (no genera nada) |
| `false` | estás seguro de que **NO** lo lleva | **candidato a infracción** |
| `unknown` | **no se puede saber** (lejos, ocluido, borroso) | **nada** — no cuenta ni a favor ni en contra |

En el parser, solo `true`/`false` se mapean a booleanos; `unknown` (y cualquier
atributo ausente) se lee como `None`, y **`None` corta la corrida de violación**.
Es decir: un tramo `unknown` nunca fabrica una infracción.

Por eso el atributo es `radio` con default `unknown` y **no** checkbox con default
`false`. Con checkbox, cada persona que dibujaras y no tocaras quedaría exportada
como `false` = "sin casco", inventando una infracción sobre alguien que sí llevaba
EPP. Con `unknown` por default, **la incertidumbre es el estado seguro**: si no lo
tocás, no acusás a nadie.

Regla operativa: poné `true`/`false` **solo donde lo veas con seguridad**. Ante la
duda genuina (persona muy lejana o tapada), dejá `unknown`. No es pereza — es
correcto: un `unknown` honesto vale más que un `false` adivinado.

---

## 5. De la anotación al GT: qué hace `derive_clip_gt.py`

Todo lo que dibujaste se exporta como XML `CVAT for video 1.1` y la derivación lo
convierte en `clip_gt.v2`. La cadena de razonamiento es:

### 5.1 Timeline de atributos → intervalos de violación

Para cada track y cada condición, la derivación construye el estado frame a frame
(escalón) y detecta las **corridas contiguas de `false`** (violación sostenida).
`true` y `unknown/None` cortan la corrida. `outside` la corta (fin del episodio);
`occluded` **no** la corta.

Un intervalo = "la persona X estuvo sin casco desde el ms A hasta el ms B".

### 5.2 Umbral de persistencia → episodios vs sub-umbral

No toda violación es un episodio. Cada condición tiene una **persistencia mínima**
(el tiempo que el motor de alertas real espera antes de confirmar):

| Condición | Persistencia mínima (default) |
|---|---|
| CR-01 (casco) | **4000 ms** |
| CR-02 (chaleco) | **7000 ms** |

Estos defaults están **alineados con el pattern set oficial del motor**
(`cr01_cr02_v2.yaml` del control-plane). Entonces:

- Intervalo **≥ persistencia mínima** → **episodio** (`episodes[]`): una infracción
  de verdad que el sistema debería alertar.
- Intervalo **< persistencia mínima** → **evento sub-umbral**
  (`sub_threshold_events[]`): un transitorio que el sistema **no** debe alertar.
  Igual se registra, porque sirve para verificar que el motor **no** dispara de más.

Por eso importa buscar transiciones cortas que el suavizado del detector pudo
comerse: esos transitorios sub-umbral son parte del GT (verifican los falsos
positivos del motor).

### 5.3 Nivel escena (scene) vs sujeto (subject)

El `clip.yaml` de cada clip declara un `level`:

- **`scene`** (default, lo que usa `cb_b01_p7`): el GT son episodios de
  **escena-condición**. Primero se umbrala **por track**, y los sobrevivientes se
  **fusionan** en episodios de escena. `subjects_in_evidence` = máximo de personas
  concurrentes en violación. Es el nivel que matchea el motor de alertas para las
  métricas (recall/precision).
- **`subject`**: un episodio por track, con `subject_label` (`persona_A`,
  `persona_B`, …). Es para comparación cualitativa; no se usa para métricas 1:1.

El orden "umbralar por track ANTES de fusionar" es deliberado: fusionar primero
crearía episodios de escena que ningún individuo sostuvo, y el motor (que es 1:1
por sujeto) los contaría como `missed`, deprimiendo el recall falsamente.

### 5.4 El timeline legible

Al correr la derivación imprime un timeline por episodio y sub-umbral. **Ese es tu
último control**: lo leés contra el video. Si un episodio no coincide con lo que
viste, volvés a CVAT y corregís. La aritmética es del script; la verdad es tuya.

Ejemplo de salida:

```
=== cb_b01_p7  (00:24.433, 30 fps, negative=False) ===
  EPISODIO  ep1  CR-01  00:03.200 → 00:09.500  [2 sujeto(s)]
  sub-umbral       CR-02  00:12.000 → 00:14.100  (transitorio < persistencia mínima (2100 ms < 7000 ms) — NO debe alertar)
Revisar contra el video antes de promover al banco.
```

---

## 6. Errores comunes (y las guardas que los atrapan)

La derivación **falla ruidosamente** en vez de producir un GT silenciosamente malo:

| Síntoma | Causa | Fix |
|---|---|---|
| *"no se encontró ningún track con label 'person'"* | exportaste en formato equivocado (`CVAT for images` en vez de `CVAT for video 1.1`), o el label quedó `Person`/`Persona` | re-exportar en `CVAT for video 1.1`; label exacto `person`. Si el clip es un negativo real, correr con `--allow-empty` |
| *"el `<size>` del XML difiere de n_frames"* | la task se creó sobre otro video (o el crudo de `raw/`) | rehacer la task con el `.mp4` de `clips/` |
| infracción que no ocurrió | dejaste un atributo en `false` sin querer, o un checkbox mental | revisar: `false` solo donde lo viste; ante duda `unknown` |
| episodio cortado de más | marcaste `outside` en una oclusión | oclusión = `occluded`, no `outside` |
| persona detectada un instante y desaparece | la dibujaste como **Shape**, no Track | redibujar como Track |

Estas guardas existen porque un GT malo que "pasa" es peor que un pipeline que
falla: contamina el banco y arrastra el error a las métricas del sistema evaluado.

---

## 7. El flujo completo de una sesión (resumen)

Presupuesto esperado: **5–10 min por clip de 30 s** con 1–3 personas (vs 30–60 min
de anotación manual densa). Obra real multi-persona (P7) lleva más, sobre todo por
unir tracks fragmentados.

1. **Mirar el clip entero** una vez, sin tocar nada (contexto).
2. **Tracks:** borrar falsos positivos de persona; **unir** (merge) ids que son la
   misma persona partida en varios tracks; **separar** (split) un track que saltó de
   una persona a otra; ajustar cajas gruesas lo justo. Marcar `outside` solo en
   salidas reales; oclusiones → `occluded`.
3. **Agregar** las personas que el detector no vio (dibujar Track nuevo, seguirlo,
   cerrarlo con `outside` al salir).
4. **Atributos** (lo más importante para el GT): recorrer cada transición de
   `has_helmet`/`has_vest` y verificarla contra el video; buscar transiciones cortas
   faltantes; poner `true`/`false` donde hay certeza, `unknown` donde no.
5. **Exportar** el XML (`CVAT for video 1.1`) a `corrected/<clip>.xml`.
6. **Derivar** (`derive_clip_gt.py`) y leer el timeline contra el video.
7. **Validar** (`validate_clip_gt.py`).

Los comandos concretos de export/derive/validate están en
[`../GUIA-CVAT.md`](../GUIA-CVAT.md) §5–7.

---

## 8. Glosario rápido

- **Task / Job:** unidad de trabajo sobre un clip / espacio de anotación dentro de ella.
- **Track:** caja que sigue a un objeto a lo largo del video (lo que usamos).
- **Shape:** caja en un único frame (no lo usamos en video).
- **Keyframe:** frame donde fijás explícitamente posición/estado; CVAT interpola entre keyframes.
- **`outside`:** el objeto salió de cuadro; cierra el episodio.
- **`occluded`:** el objeto está tapado pero sigue ahí; no cierra nada.
- **Atributo mutable (escalón):** valor que se mantiene hasta el próximo keyframe que lo cambie.
- **`unknown`:** estado "no evaluable"; nunca fabrica una infracción. Default y estado seguro.
- **CR-01 / CR-02:** condición casco (`has_helmet`) / chaleco (`has_vest`).
- **Episodio:** violación que supera la persistencia mínima; el motor debería alertarla.
- **Sub-umbral:** violación demasiado corta; el motor **no** debe alertarla (verifica FP).
- **CFR:** constant frame rate; garantiza que `frame → ms` sea exacto.
- **clip_gt.v2:** el JSON de GT final que produce la derivación.
```
