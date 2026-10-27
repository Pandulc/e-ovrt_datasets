# Revisión dirigida del GT del banco temporal (octubre de 2026)

**Qué es.** La constancia de una revisión de la referencia temporal (GT) del rodaje, hecha
en lugar de una doble anotación al azar. Atiende la limitación de una referencia sin segunda
revisión. Todo lo que se cita acá está en esta carpeta o en el repo;
las imágenes de la revisión no se versionan (son de personas) y se regeneran con
`datasets/scripts/videogt/revision/preparar.py`.

## 1. Qué clips se revisaron y por qué

Se revisaron **8 clips del rodaje**, elegidos con criterios que **no miran la salida del
modelo** (ni alertas ni métricas):

| Criterio | Clips |
|---|---|
| Inicio del episodio a más de 0,5 s de la marca que el operador registró al recortar la toma (`datasets-videos/docs/ficha-eventos-rodaje.md`) | `a_p2_c01`, `a_p2_c02`, `a_p7_c02`, `a_p9_c08` |
| Cantidad de episodios distinta entre esa marca y el GT | `a_p1_c05`, `a_p7_c03` |
| Cambio de atributo de menos de 1,5 s dentro de una infracción | `a_p1_c05`, `a_p2_c05`, `a_p7_c03`, `a_p8_c01` |
| Trayectoria que termina y otra que empieza a menos de 3 s y cerca, alrededor de una infracción, o caja suelta sin cierre | `a_p7_c02`, `a_p7_c03`, `a_p8_c01` |

Se escanearon los 47 clips del banco con los mismos criterios estructurales. `a_p4_c02`,
`a_p5_c01` y `a_p9_c06` tienen cajas de un cuadro al entrar o salir de cuadro, **sin efecto
sobre ningún episodio**, y no se revisaron. Los 13 clips de obra real ya tenían una revisión
a ciegas de sus episodios (estrato B) y no tienen cajas sueltas.

## 2. Cómo se revisó

- Una vista local (`datasets/scripts/videogt/revision/`) mostró, para cada caso, los cuadros
  del clip con las cajas de la anotación y una pregunta neutra (318 respuestas en total:
  identidad de cada caja, si la persona estaba tapada o fuera de cuadro, y el estado del casco
  o del chaleco cuadro a cuadro). **La vista no mostraba el valor anotado, las alertas del
  sistema ni ninguna métrica.** Especificación: `datasets-videos/docs/revision-dirigida-2026-10.yaml`.
- **Revisión asistida por IA.** Las respuestas las propuso Claude (Anthropic) leyendo los
  mismos cuadros, con una justificación por caso que señala el rasgo que decide cada respuesta
  (`propuesta_claude.json`), y las validó el revisor del equipo (`simon`). El revisor había
  respondido antes 50 de las 318 por su cuenta (`respuestas.antes-de-propuesta.json`).
  **Acuerdo entre ambos: 314 de 318 (98,7 %).** Las 4 diferencias son cuadros de identidad
  donde las dos personas se superponen en la caja: el revisor respondió «no se distingue» y la
  propuesta, P o Q. Manda el revisor.
- La validación final la declaró el revisor por escrito («todo validado, es correcto todas tus
  respuestas») y quedó registrada en `respuestas.json` (`validacion`), con la aclaración de
  que la vista no registró clics de validación (la página abierta era anterior a la precarga).
- Las respuestas se convirtieron en correcciones con reglas fijas y declaradas
  (`datasets/scripts/videogt/revision/convertir.py`, R1–R5), que **nunca pisan un valor
  explícito del anotador con una inferencia**: un `unknown` toma el estado que el revisor
  sabe; un valor explícito solo cambia si el revisor vio otra cosa en ese cuadro.

## 3. Qué se encontró

- **En los dos clips con cruces de personas (P7)** la persona se saca el casco, lo deja sobre
  la mesa (visible todo el tramo) y queda tapada por un compañero que se le cruza adelante.
  La anotación cortó su trayectoria en cada cruce en vez de mantenerla como `occluded`
  (protocolo del anotador, `datasets-videos/docs/etiquetado-cvat.md` §7.1). Como el GT umbrala
  la persistencia por trayectoria, el episodio se partía o empezaba tarde. En `a_p7_c02` hubo
  además un **intercambio de identidad** a los 27,0 s, y en `a_p7_c03`, **tres cajas de un
  cuadro sin cierre** que CVAT extiende hasta el final del clip.
- **Inicios y finales de chaleco** marcados cuando el chaleco ya estaba en la mano, no cuando
  dejó de estar sobre los dos hombros (§7.3: «colgado de un hombro» cuenta como no puesto).
- **Un parpadeo de 0,6 s** (`a_p1_c05`) que marcaba el casco puesto cuando estaba sobre la mesa.
- **Una corrección en contra del sistema:** en `a_p9_c08` la infracción estaba marcada desde
  que la persona entra a cuadro (2,30 s), antes de que su cabeza sea visible (2,60 s).

Herramienta nueva para las correcciones de identidad: `datasets/scripts/videogt/apply_identity_corrections.py`
(18 tests). Cadena: `split_cvat_project → apply_adjudications → apply_identity_corrections →
apply_attribute_corrections → derive_clip_gt`. Las correcciones están firmadas en cada
`<clip>.clip.yaml` (`annotation.identity_corrections` y `annotation.attribute_corrections`) y
copiadas en `correcciones/`.

## 4. Qué cambió en el GT

21 correcciones de identidad y 29 de atributo (251 cajas).

| Clip | Episodios antes (s) | Episodios después (s) |
|---|---|---|
| `a_p7_c02` | CR-01 13,20–26,93 | CR-01 3,03–29,73 |
| `a_p7_c03` | CR-01 3,00–8,07 · CR-01 11,60–32,53 | CR-01 3,00–28,53 |
| `a_p1_c05` | CR-01 3,90–12,70 · CR-01 13,30–18,40 | CR-01 3,90–18,40 |
| `a_p2_c01` | CR-02 4,43–29,40 | CR-02 3,13–29,40 |
| `a_p2_c02` | CR-02 5,10–32,50 | CR-02 3,63–32,50 |
| `a_p9_c08` | CR-01 2,30–22,03 | CR-01 2,53–22,03 |
| `a_p2_c05` | CR-02 3,23–31,80 | CR-02 3,23–34,23 |
| `a_p8_c01` | CR-01 3,07–16,03 · CR-01 31,10–43,30 | CR-01 3,07–15,87 · CR-01 31,03–43,30 |

- **Banco:** 47 clips, 32 positivos y 15 negativos (sin cambios); **35 episodios** (antes 37:
  dos episodios partidos se reunificaron). Rodaje: 33 episodios, 33 evaluables (antes 35 y 34).
- **Concordancia con la marca del operador:** 32 de 33 inicios dentro de 0,5 s y 33 de 33 dentro
  de 1 s (antes 29 y 30); ningún clip con distinta cantidad de episodios (antes 2). La mejora es
  en parte por construcción —los clips se eligieron por esas discrepancias—, pero cada corrección
  salió de la imagen, no de alinear el GT a la marca.
- **Reproducible desde la fuente:** regenerar los 8 clips desde el export de CVAT con la cadena
  completa da XML y GT idénticos byte a byte. `validate_clip_gt`: 0 errores; `sha256sum -c`: 189 OK.
- **Huellas:** la del archivo que cubre el GT, `clip_bench.sha256`, pasa de `c096b16d…` a
  `df45a01cdb99bd098e658acb7d4b28686fd11616fb432980288ddcd268bc3b57`. La de `manifest.yaml`
  (`3f14f50a…`) **no cambia, porque no cubre el GT** (lista los clips y sus videos): para
  identificar la versión de la referencia hay que citar la de `clip_bench.sha256`.

## 5. Efecto sobre las campañas de la generación 1 (informativo)

Mismas alertas, mismo evaluador; antes, el GT anterior reproduce exactamente las cifras
publicadas (control). Detalle: `docs/operacion/datos/134-piloto-gt02-sensibilidad-bordes/gt_corregido_efecto.json`.

| Campaña | F1 publicado | F1 con el GT corregido |
|---|---|---|
| T1 escena | 0,789 | **0,841** |
| G1 sujeto | 0,930 | **0,899** |
| T2 base-560 | 0,704 | 0,714 |
| D1 E-DIR | 0,160 | 0,162 |
| H1 fusión | 0,296 | 0,325 |
| B1 bare_head | 0,377 | 0,412 |
| R1 / R2 (≈4,29 fps) | 0,794 / 0,866 | 0,746 / 0,831 |
| R3 / R4 (≈2,00 fps) | 0,738 / 0,875 | 0,719 / 0,812 |
| R5 / R6 (≈1,15 fps) | 0,646 / 0,742 | 0,615 / 0,677 |
| I1 / I2 (obra real) | 0,333 / 0,190 | sin cambios |

**La ganancia por identidad (G1 − T1) baja de +0,141 a +0,058.** La causa está en el cruce de
`a_p7_c02`: el rastreador del sistema pierde la identidad de la persona en el mismo cruce en
que la había perdido la anotación, y la alerta por sujeto llega a los 17,3 s (14 s después del
inicio). Con el GT anterior —partido en el mismo lugar— esa alerta tardía coincidía con un
episodio que empezaba a los 13,2 s y contaba como acierto; con el GT corregido es un episodio
perdido. **La referencia anterior premiaba a la granularidad por sujeto justo donde su
rastreador falla.** Las conclusiones comparativas se mantienen (sujeto por encima de escena
en cada densidad; el campeón por encima de base-560; E-DIR, la fusión y bare_head por debajo),
pero con márgenes menores.

**Sensibilidad a los bordes sobre el GT corregido** (GT-02: 5.000 referencias simuladas con
cada borde corrido al azar hasta ±0,5 s, la misma para todas las campañas; detalle en
`docs/operacion/datos/134-piloto-gt02-sensibilidad-bordes/gt02_todas_gt_corregido.json` y
`gt02_extra_gt_corregido.json`):

| Conclusión | GT anterior | GT corregido |
|---|---|---|
| Ganancia por identidad (G1 > T1) | 100 % · rango [+0,056; +0,141] | **91,0 %** · rango **[0,000; +0,058]**, media +0,039 |
| Sujeto > escena en cada densidad | 100 % | 100 % |
| Campeón ≥ base-560 · E-DIR, fusión y bare_head por debajo · FP en obra real escena < sujeto | ≥ 99,98 % | 100 % |

Con ±1 s, la ganancia por identidad es positiva en el 75 % de las referencias (rango
[−0,029; +0,075]). **Leída con la referencia corregida, la ganancia por identidad es chica y
sensible a la precisión del inicio anotado**; las demás conclusiones comparativas no cambian.

Estas cifras son de la generación 1 (validación inicial). La evaluación final (generación 2)
usa el GT corregido.
