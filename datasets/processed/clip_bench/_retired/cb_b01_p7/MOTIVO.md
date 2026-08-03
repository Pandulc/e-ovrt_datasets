# `cb_b01_p7` — retirado del banco de clips (2026-08-03)

Clip de **bring-up** del video-gt-lab: con él se probó la cadena completa del
spec 43 el 2026-07-11 y se obtuvo el primer benchmark temporal real
(P=0,5 R=1,0 F1=0,67, t_alert=4000 ms, TTFD=0 ms, SDR=0,999 — doc 54).
Cumplió ese propósito. **No es un clip de medición.**

## Por qué se retira

1. **Licencia/consentimiento sin registrar — motivo vinculante.** Es obra real
   (Bloque B, no guionado) con ~10-12 operarios identificables. Su propio
   `clip.yaml` lo condiciona: *"LICENCIA/CONSENTIMIENTO: registrar en
   registry/license_registry.md antes de usarlo en resultados reportables
   (spec 43 §7) — pendiente."* Verificado el 2026-08-03: **no está registrada**.
   Esto **no se resuelve con una pasada de CVAT**, así que anotarlo no habría
   desbloqueado la reportabilidad.
2. **El GT lo produjo una IA**, no un humano: `annotation.annotator:
   claude-vision-preliminary` (revisión visual por crops, sin pasada frame a
   frame). Estado `gt_preliminary`. Inadmisible dentro de un banco de medición.
3. **El GT no discrimina.** Un único episodio de escena CR-01 de
   **0 → 24.433 ms** cubre el 100% del clip: el recall queda trivialmente
   satisfacible (cualquier alerta, en cualquier instante, matchea) y el onset en
   0 ms viola el pre-roll `MIN_ONSET_MS = 2000` — el TTFD colapsa a 0 como
   artefacto de recorte, no por mérito del sistema (es exactamente el TTFD=0 ms
   que quedó registrado en aquel benchmark).
4. **Su aporte ya está cubierto.** El escenario P7 tiene 5 clips del rodaje con
   GT humano, y la diversidad de fuente no guionada la aportará el lote de
   clips de internet (14, en anotación al 2026-08-03).

## Qué se conservó

Los 5 artefactos, con el layout del banco (`meta/`, `gt/`, `preann/`,
`annotations/`). El `.mp4` **sigue en su lugar**, en
`datasets/raw/clip_bench/clips/cb_b01_p7.mp4` (gitignorado), así que el clip
sigue disponible como **clip de humo para pruebas de plataforma** — lo que no
es es parte del banco de medición.

La evidencia histórica del bring-up no depende de esto: vive en los docs 54 y
50, y en `docs/operacion/datos/95-2026-07-12-bench-cb_b01_p7-*`.

## Cómo revertirlo

Volver a mover los artefactos a sus directorios en `clip_bench/` y re-promover:

```bash
python3 datasets/scripts/bench/promote_clip.py --clip-id cb_b01_p7 --lab-dir <dir-con-el-clip>
```

(o restaurar la fila en `manifest.yaml` y re-ensamblar con
`build_clip_bench.py`). Antes de hacerlo: registrar la licencia y reemplazar el
GT por una pasada humana en CVAT — los dos motivos siguen en pie hasta entonces.
