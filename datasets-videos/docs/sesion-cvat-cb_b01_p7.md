# Hoja de ruta: pasada humana en CVAT sobre `cb_b01_p7`

Guía específica para la sesión de corrección de este clip. Las reglas generales de
decisión están en [`etiquetado-cvat.md`](./etiquetado-cvat.md) §7 (leelas antes);
los pasos operativos (crear task, importar, exportar) en [`../GUIA-CVAT.md`](../GUIA-CVAT.md).

## Estado de partida

Hay **dos** XML previos, y ninguno es GT humano:

| Archivo | Qué es | Sesgo |
|---|---|---|
| `preann/cb_b01_p7.xml` | GDINO + ByteTrack crudo: **38 tracks**, decenas de transiciones de atributos (mucho flicker de detección) | recall alto, muchos falsos positivos y micro-tracks |
| `corrected/cb_b01_p7.xml` | Revisión visual **preliminar de Claude** (no humana): aplastó casi todos los atributos a `true/true`, dejó los tracks chicos en `unknown`, borró los tracks 10/14/26/34, y dejó al **track 11** como único violador (`has_helmet=false` los 24,4 s) | conservador; pudo haber borrado violaciones reales al descartar el flicker de GDINO |

El GT derivado actual (`gt/cb_b01_p7.json`, estado `gt_preliminary`) tiene **un solo
episodio: CR-01 de 0 a 24 433 ms, 1 sujeto** (el track 11). Cero episodios CR-02 y
cero sub-umbrales. La pasada humana confirma o refuta exactamente eso.

**Recomendación de arranque:** importar `corrected/` como base (mucho menos ruido
que la preann) pero tratarla como **hipótesis a auditar**, no como verdad: los
puntos calientes de abajo vienen de lo que GDINO propuso y la corrección preliminar
descartó — cada uno se re-adjudica mirando el video. Si el equipo prefiere máxima
independencia (sin heredar el sesgo de la revisión preliminar), puede partir de la
preann cruda; cuesta más por el flicker.

## Lo que la sesión tiene que decidir (en orden de importancia)

### 1. El track 11 — el episodio CR-01 entero depende de él

Según la revisión preliminar, es el **operador del compactador**, resultado de
**fusionar los tracks GDINO 11 + 14 + 26** en una sola identidad, extendida a todo
el clip (frames 0–732) con `has_helmet=false` constante. Verificar contra el video:

- [ ] ¿La fusión es correcta? Mirar con cuidado las **costuras** (~f=42–97 donde el
  11 original se cortaba con `outside`, y ~f=282–430 donde empalman 14 y 26): que no
  haya saltado a otra persona.
- [ ] ¿Está **realmente sin casco los 24 s**? ¿O hay tramos donde no se puede saber
  (→ `unknown`, que parte el episodio)?
- [ ] ¿`has_vest`? Hoy está `true`; GDINO proponía `false` en varios tramos de esos tracks.

Cualquier cambio acá cambia el único episodio del GT.

### 2. Los tracks borrados — confirmar los veredictos de la revisión preliminar

La revisión preliminar borró tracks de GDINO con estos veredictos; son plausibles
pero no humanos, así que se confirman de un vistazo:

- [ ] **Track 10** (frames 0–732, GDINO: `helmet=false, vest=false` constante):
  veredicto preliminar = **caldera de brea** (no persona). Si en realidad fuera una
  persona, sería un segundo violador CR-01 de clip completo — vale el vistazo.
- [ ] **Track 34** (f=543–676): veredicto preliminar = **pisón** (máquina).
- [ ] Tracks 14 y 26: **no borrados sino fusionados** dentro del track 11 (ver §1).

### 3. Puntos calientes de atributos (GDINO dijo `false`, la corrección lo descartó)

Para cada uno: ir al rango de frames, mirar, y decidir `true`/`false`/`unknown`
según §7.3. El flicker de <1 s casi seguro es ruido de detección; los tramos
sostenidos (≥2–3 s) son los que pueden ser violaciones reales perdidas —
**especialmente los de chaleco: el GT actual no tiene ningún episodio CR-02.**

| Track | Rango (s) | GDINO proponía | Prioridad |
|---|---|---|---|
| 4 | 9,9 → 12,8 | `vest=false` sostenido ~2,9 s | **alta** |
| 3 | 13,9 → 15,5 | `vest=false` ~1,6 s (+ `helmet=false` 14,5–15,3) | media |
| 9 | 10,7 → 15,8 (outside) | `vest=false` sostenido ~5 s hasta salir | **alta** |
| 15 | 4,3 → 6,1 | `helmet=false` ~1,8 s (+ `vest=false` 4,5–5,5) | media |
| 15 | 14,5 → 16,4 (outside) | `helmet=false` ~1,9 s hasta salir | media |
| 20 | 19,0 → 21,2 (outside) | `helmet=false` ~2,2 s hasta salir | **alta** |
| 8 | 1,7 → fin | `helmet=false` sostenido ~23 s (corrected lo dejó `true`) | **alta** |
| 5 | 7,9 → 8,6 (outside) | `vest=false` al salir | baja |
| 1 | 3,8 → 4,8 (outside) | `vest=false` al salir | baja |
| 30 | 19,6 → 23,7 | flicker de casco (3 cambios) | media |
| 31 | 20,4 → 24,4 | flicker de casco (5 cambios en 4 s) | media |
| 16 / 20 / 25 | 7,4–8,6 / 8,0–9,9 / 9,8–11,8 | flicker de chaleco (<1 s por tramo) | baja (probable ruido) |
| 29 | 14,3 → 14,5 | `helmet=false` 0,2 s | baja (probable ruido) |

Ojo con §7.5: varios candidatos de chaleco andan cerca de los 7 s de persistencia
de CR-02 — anotarlos honestos y avisar si quedan filo de navaja.

### 4. Micro-tracks: ¿personas reales, fragmentos, o falsos positivos?

Tracks de un puñado de frames. Para cada uno: **borrar** si no es una persona,
**merge** si es un fragmento de otra persona ya trackeada, dejar (con atributos
`unknown` si no se evalúa) solo si es una persona real distinta:

- [ ] 12 (2 frames), 33 (2), 27 (2), 19 (3), 21 (3), 32 (3), 36 (3), 13 (4),
  17 (4, GDINO le veía `vest=false`), 18 (5), 22 (5), 23 (9)

### 5. Personas que nadie anotó (pasada anti-anclaje)

- [ ] Una pasada del clip completo **con las anotaciones ocultas** buscando personas
  sin track. Es el punto ciego correlacionado: lo que GDINO no pre-anotó es lo que
  el sistema evaluado también va a fallar (etiquetado-cvat.md §7.4, punto 3).

## Cierre de la sesión

1. Export `CVAT for video 1.1` → `corrected/cb_b01_p7.xml` (pisa el preliminar).
2. `derive_clip_gt.py` → leer el timeline contra el video (episodios esperables:
   el CR-01 del track 11 si sobrevive; cualquier CR-02 nuevo es hallazgo).
3. `validate_clip_gt.py`.
4. Actualizar `annotation.annotator` en el flujo de derivación (deja de ser
   `claude-vision-preliminary`) y promover el estado `gt_preliminary` → `gt_ready`
   en el manifiesto.

Presupuesto realista: este clip es obra real (P7) con ~15 personas reales y mucha
maquinaria — estimar **45–90 min**, no los 5–10 min de un clip simple. La mayor
parte va a identidad de tracks y a la tabla de puntos calientes; las cajas se
ajustan lo justo (§7.4).
