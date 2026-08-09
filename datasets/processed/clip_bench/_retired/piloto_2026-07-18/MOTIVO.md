> ## ✎ 2026-08-06, MISMO DÍA: LOS VIDEOS SE RECUPERARON
>
> El usuario los bajó de CVAT. **Verifican exacto contra el GT** (1920×1080, 30 fps,
> 360 frames, 12,000 s — los tres campos que este doc daba por reconstruidos) y el GT
> re-derivado con el `info.json` real es **idéntico** al derivado sin video.
>
> **Lo que cambia:** los 4 vuelven al laboratorio (`datasets-videos/`) y **son
> ejecutables**. Se les midió **Nivel A (estado por persona)** contra su GT humano —
> ver **`docs/operacion/105`**, que es donde vive el resultado.
>
> **Lo que NO cambia:** siguen **fuera del banco de Nivel B**. Sus 4 episodios están
> censurados por el gate A1 (12 s) y eso no depende de tener el archivo. Todo lo que
> dice este documento sobre por qué no son clips de medición temporal sigue en pie; lo
> único que caducó es "no son ejecutables".
>
> Esta carpeta queda como **registro histórico** del período sin video.

# Piloto 2026-07-18 — 4 clips anotados que NO entran al banco de medición

**Qué son.** Los cuatro primeros clips que se anotaron en CVAT, el 2026-07-18,
recortados a **12 s** de videos del pool de internet (los 16 de
`@HospitalConstruction`, ver `registry/license_registry.md` §Material de VIDEO)
cuando la convención de nombres todavía era `videoNN_clipMM`. Se anotaron para
probar el laboratorio de GT; con ellos se descubrió que **los clips cortos no
sirven para las métricas temporales**, y esa conclusión disparó el doc 57 y el
gate de dimensionamiento A1 (doc 58).

Las anotaciones se recuperaron y procesaron el **2026-08-06** (doc 102). No se
promueven al banco: se conservan acá, con GT derivado, **como evidencia del
análisis de duración de clips**.

| clip | tracks | GT (humano) | avisos de dimensionamiento |
|---|---|---|---|
| `video02_clip07` | 14 | 1 ep CR-02 `0 → 12.000 ms`, 1 sujeto | onset 0 ms · censura t_alert |
| `video15_clip01` | 5 | 1 ep CR-02 `0 → 12.000 ms`, **2 sujetos** | onset 0 ms · censura t_alert |
| `video16_clip10` | 11 | 1 ep CR-02 `0 → 11.933 ms`, 1 sujeto, 7 sub-umbral | onset 0 ms · censura t_alert |
| `video16_clip14` | 10 | 1 ep CR-02 `2.467 → 12.000 ms`, 1 sujeto | censura t_alert |

## Por qué no entran al banco

1. **El `.mp4` no existe.** Se perdió en el renombre de clips a `vXX_cXX`
   (commit `9fdc9f9f`, "renombre de clips a esquema vXX_cXX y limpieza del
   bloque B viejo"). Sin video no hay corrida del media-plane, así que **no hay
   detección, ni alerta, ni evaluación posible**: el GT no tiene contra qué
   medirse. `promote_clip.py` los rechaza por diseño (exige `mp4`, `info.json`,
   `clip.yaml` y `preann`; faltan el primero y el último).
2. **Los cuatro están censurados por el gate A1** — y ése es justamente su valor
   (abajo). Un clip de 12 s no alcanza a cubrir `onset + t_alert_upper + resolve
   + cola`: para CR-02 hacen falta 25 s desde el onset y hay 12.
3. **Tres de los cuatro tienen el onset en `t = 0`**: sin pre-roll, el TTFD
   colapsa a 0 como artefacto del recorte, no por mérito del sistema.

## Para qué SÍ sirven

**Son la evidencia empírica, con GT humano, de la tesis del doc 57 §6.5/§6.7:**
la duración del clip no es una preferencia estética sino el presupuesto de tiempo
que las métricas necesitan para existir. Antes esa afirmación se apoyaba en un GT
*preliminar* (pre-anotación GDINO) de un solo clip; ahora se apoya en **4 clips
anotados a mano: 4/4 con el episodio censurado y 3/4 sin pre-roll, 7 avisos de
dimensionamiento en total**. Ningún recorte de 12 s del material sobrevivió al
gate.

**`video16_clip10` cierra además dos cosas:**
- Es el clip que doc 57 cita como caso testigo (`episodio 0→11933 ms`,
  `TTFD = 0` por construcción) y contra el que doc 58 verificó el gate A1. El GT
  **humano** reproduce el mismo intervalo `0 → 11.933 ms`: aquel hallazgo no era
  un artefacto de la pre-anotación automática.
- Esa coincidencia exacta **valida la reconstrucción de `info.json`** (ver
  abajo): 358 frames a 30 fps son 11.933 ms exactos.
- Su metadata provisional de julio (commit `52a2d6e4`) lo declaraba `scenario:
  P7` ("dos personas, una infringe"). El GT humano deja
  `subjects_in_evidence: 1`: **P7 no se sostiene**, es P2.

## Qué se reconstruyó, y con qué evidencia

`meta/*.info.json` está **reconstruido** (lleva `reconstructed: true`), porque lo
producía `prepare_clip.sh` a partir del `.mp4` que ya no está:

| campo | valor | de dónde sale |
|---|---|---|
| `n_frames` | 360 (los 4) | `./meta/task/size` del XML de CVAT |
| `resolution` | 1920x1080 | `./meta/task/original_size` del XML |
| `fps` | 30 | (a) los masters del lote son 1920×1080 @ 30 fps, medido sobre las 14 pre-anotaciones; (b) doc 57 registra el clip como "12,000 s exactos" y el episodio en `0→11933 ms` — 358 frames a 30 fps dan 11.933 ms **exactos** |
| `duration_ms` | 12.000 | `n_frames × 1000 / fps` |
| `sha256` | `null` | **no verificable**: no hay archivo que hashear |

El `fps` es el único número inferido, y la vía (b) lo confirma por aritmética
independiente. Si alguna vez reaparece el `.mp4`, verificar `sha256` y `fps`
antes de usarlo para cualquier cosa que no sea este análisis.

## Layout

```
_retired/piloto_2026-07-18/
├── MOTIVO.md                  ← este archivo
├── annotations/<clip>.xml     ← export CVAT for video 1.1, task-level (lo humano)
├── meta/<clip>.clip.yaml      ← escenario asignado CONTRA el GT, licencia, anotador
├── meta/<clip>.info.json      ← RECONSTRUIDO (ver arriba)
└── gt/<clip>.json             ← clip_gt.v2 derivado, `validate_clip_gt` 0 errores
```

No hay `preann/`: la pre-anotación de estos cuatro también se perdió en
`9fdc9f9f`. Los XML de `annotations/` son corrección humana, no pre-anotación.
