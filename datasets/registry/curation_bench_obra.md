# Curación `bench_obra` — sub-splits limpios del BENCH v2 (2026-07-23)

**El original NO se modifica.** `processed/coco/bench/construction_site_safety_bench.json`
queda intacto como instrumento histórico (comparabilidad con Sprint 2). La curación es un
artefacto derivado aparte en `processed/coco/bench/curated/`, regenerable con:

```bash
python3 datasets/scripts/curate/build_bench_obra.py
```

## Por qué

Auditoría S0 del plan maestro de experimentos (`docs/operacion/63` del repo `docs`,
2026-07-23): el dataset Roboflow `construction_site_safety` mezcla fuentes que no son obra —
selfies indoor con barbijo COVID (con `bare_head` anotado sobre el pelo), imágenes de PASCAL
VOC (incl. un `vest` mal etiquetado sobre una camisa a cuadros), aeropuerto, casino, karting —
y trae 4 bboxes `bare_head` de ~2×2,5 px (indetectables por diseño). Medido: la contaminación
**inflaba el recall CR-01 ≈2×** (los selfies sin casco eran "violadores" triviales) y
**deprimía el AP de vest** (`docs/operacion/64`).

## Qué se ajustó exactamente respecto del original

Reglas (codificadas en el script, testeadas en `datasets/tests/test_bench_obra.py`):

1. **Exclusión por prefijo de archivo** (12 prefijos, tabla completa en el script y en
   `curated/bench_obra_manifest.json` con la lista imagen-por-imagen y su causa):
   `IMG_`, `Movie-on`, `Mask2`, `RPReplay`, `YouTube_FreeStock`, `airport_inside`, `casino`,
   `bookstore`, `Inside-merge`, `autox`, `2008_`, `2009_` → **49 imágenes excluidas**.
2. **Área mínima de bbox 9 px²** → **4 anotaciones `bare_head` sub-pixel excluidas**.

| | Original | `bench_obra` | Δ |
|---|---|---|---|
| Imágenes | 196 (82 test + 114 val) | **147** (62 test + 85 val) | −49 (−25%) |
| person | 340 | 262 | −78 |
| helmet | 189 | 159 | −30 |
| vest | 102 | 79 | −23 |
| bare_head | 110 | **61** | −49 (−45%) |

Nota: casi la mitad del GT de `bare_head` era contaminación (selfies) o sub-pixel — la
debilidad de la clase debe leerse contra el n limpio (61), no contra 110.

## Uso

Los números de tesis (Q1) se reportan sobre `bench_obra` con la contaminación del original
declarada; el BENCH completo queda para comparabilidad histórica y como apéndice
(`docs/operacion/64 §Decisiones`). Evaluación del media-plane contra el sub-split:

```bash
python -m eovrt_media.tools.evaluate --run runs/<run_id> \
  --bench-coco ../e-ovrt_datasets/datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_test.json
```

(usar el archivo del split que corresponda al run: `_test` o `_val`).
