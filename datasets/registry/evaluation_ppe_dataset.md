# Evaluación de candidato: `ppe-dataset` (Roboflow "PPE 6 classes" v6) — RECHAZADO para BENCH (2026-07-23)

Candidato agregado por el usuario en `datasets/raw/ppe-dataset/` (rbyz/ppe-6-classes-ntld9
v6, licencia MIT, export 2025-07-09). Análisis completo con el protocolo S0 del plan maestro
(`docs/operacion/62` §3, repo docs): integridad, GT, dominio visual, solapamiento.

## Veredicto: NO APTO para benchmarking — la curación no lo arregla

Cuatro descalificadores, cada uno suficiente por sí solo:

1. **Sin GT de `person`: la clase ancla no existe.** valid = **0** anotaciones person en 580
   imágenes; test = 17 en 581. El dataset anota las *prendas* (boots 1219, helmet 1095,
   vest 786, gloves 416, goggles 343), no a las personas. Sin person no hay AP de la clase
   ancla, no hay `person_gt`, no hay recall CR-01 a nivel persona. Es incompatible con el
   marco de evaluación canonical_v2 por construcción — ninguna regla de filtrado lo cura.
2. **Dominio equivocado.** Inspección visual (18 imgs con GT dibujado, mosaicos en el
   scratchpad de la sesión): mayoría de **fotos de producto e-commerce** (botas y cascos en
   estudio, banners "FAST DELIVERY"), selfies, calle/viajes, laboratorio escolar, frisbee —
   y **augmentations horneadas** en los archivos (collages mosaic 2×2, parches cutout negros,
   rotaciones 90°). La fracción de obra real es minoritaria.
3. **Calidad de anotación pobre a simple vista:** múltiples bboxes sistemáticamente corridas
   del objeto (varios mosaicos independientes), 20 bboxes fuera de rango [0,1], 63 imágenes
   con GT vacío en valid+test.
4. **Integridad rota:** la descarga trae 5.381 de las 17.264 imágenes declaradas; train tiene
   **86% de imágenes sin label** (3.650/4.220) y test 1.065 labels huérfanos de imágenes
   ausentes.

Agravantes: **~10% de solapamiento con `ppe_siabar`** (55/527 valid, 54/537 test, mismos
stems — no sería un bench independiente de nuestro material de TRAIN) y sin clase
`bare_head`.

## Qué se pierde al rechazarlo (y por qué igual no compensa)

Su GT de vest (786) y helmet (1095) es 5–10× el n de `bench_obra` (79/159) — tentador para el
denominador flaco de vest. Pero heredaríamos cajas corridas y dominio e-commerce: inflaría el
n con GT en el que no confiamos, que es exactamente el error que la auditoría S0 del BENCH
vino a corregir. El denominador de vest se refuerza con el **rodaje propio** (P2×3, doc 59),
no con este material.

## Disposición

- No se convierte, no se registra en `datasets_metadata.yaml` como activo, no entra a
  `configs()` de `convert_datasets.py`.
- El raw ocupa **1,2 GB** y está git-ignorado: borrarlo es decisión del usuario (no aporta a
  ningún camino del plan).
- Si a futuro se busca un bench externo de vest/helmet: exigir como criterio de entrada GT de
  `person` + dominio obra verificado a ojo ANTES de descargar (este rechazo es el precedente).
