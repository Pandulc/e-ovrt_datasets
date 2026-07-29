# Estado de avance

Fecha de corte: 2026-06-18

## Resumen v2 (activo)

Pipeline reiniciado el 2026-06-17. Vocabulario canónico v2: `person`, `helmet`, `vest`, `bare_head`.  
Datasets seleccionados: `construction_site_safety`, `chv`, `ppe_siabar` (3 activos; `construction_safety_hardhat` descartado por URL inválida).

## Avance por fase del plan v2

| Fase | Objetivo | Estado |
|---|---|---|
| 0 — Limpieza | Marcar vistas v1 como DEPRECATED, scaffold tests | Completado |
| 1 — Selección | Survey, scoring, decisión de 4 datasets v2 | Completado |
| 2 — Descarga | Descargar y registrar provenance | Completado (3/4; hardhat no disponible) |
| 3 — Conversión | canonical_v2 para todos los datasets activos | Completado |
| 4 — BENCH GT | Geometría, GT persona-nivel, auditoría | Completado (4.3 auditoría manual pendiente) |
| 5 — Splits v2 | TRAIN / BENCH / DEMO sin fuga | Completado |
| 6 — Protocolo | Protocolo experimental y prompts congelados | Completado |
| 7 — Registry | Registry, documentación y CLAUDE.md sincronizados | Completado |

## Avance por dataset v2

| Dataset | Descarga | Conversión canonical_v2 | Rol |
|---|---|---|---|
| construction_site_safety v27 | Completa (2026-06-18) | Completa | TRAIN + BENCH |
| chv | Completa (2026-06-05) | Completa | TRAIN + DEMO |
| ppe_siabar v1 | Completa (2026-06-18) | Completa | TRAIN |
| construction_safety_hardhat | No disponible (URL inválida) | — | Descartado |

## Conteos convertidos canonical_v2

| Dataset | Splits (imgs) | bare_head | helmet | vest | person |
|---|---|---:|---:|---:|---:|
| construction_site_safety | train=2603 / val=114 / test=82 | 2428 | 3551 | 3258 | 10031 |
| chv | train=1064 / val=133 / test=133 | 0 | 3538 | 1784 | 3887 |
| ppe_siabar | train=1120 / val=326 / test=161 | 0 | 1386 | 1944 | 1442 |

## Manifests de rol (datasets/splits/v2/)

| Rol | Imágenes | bare_head | helmet | vest | person |
|---:|---:|---:|---:|---:|---:|
| TRAIN | 5540 | 2318 | 8286 | 6884 | 17020 |
| BENCH | 196 | 110 | 189 | 102 | 340 |
| DEMO | 1064 | 0 | 2762 | 1396 | 3050 |

- BENCH excluido de TRAIN (sin fuga de imágenes verificado).
- vest y bare_head en BENCH < 150: limitación estructural de v27 (train muy augmentado).

## GT persona-nivel del BENCH

Archivo: `datasets/processed/coco/bench/person_gt.json` (HISTÓRICO — prohibido para evaluación, ver registry/bench_v3.md; vigente: curated/person_gt_bench_obra.json)  
Criterio: `center_in_bbox`

| Métrica | Valor |
|---|---|
| Total personas | 340 |
| CR-01 violadoras | 111 |
| CR-01 conformes | 229 |
| CR-02 violadoras | 0 (NO-Safety Vest no es clase canonical_v2) |

## Condiciones cubiertas

### CR-01 — Persona sin casco
- `construction_site_safety`: `bare_head` desde `NO-Hardhat` (negativos explícitos, D9 OK).
- `chv` y `ppe_siabar`: sin negativos explícitos; aportan positivos de alta calidad.

### CR-02 — Persona sin chaleco reflectivo
- Todos los datasets activos tienen `vest` pero ninguno tiene negativos explícitos de chaleco en canonical_v2.
- `has_vest=False` no se puede derivar del canonical_v2 actual → CR-02 GT no disponible.
- Documentado como limitación metodológica en `bench_gt_audit.md`.

## Sprint 2 — Evaluación cuantitativa BENCH v2 (2026-06-18)

Completado. 5 modelos evaluados en BENCH v2 (196 imgs, zero-shot, IoU≥0.5). Resultados completos en la tabla debajo (no existe un reporte separado; este es el registro completo del sprint).

| Modelo | mAP@50 | AP helmet | AP vest | AP bare_head | CR-01 recall E1 | FPS | VRAM MB |
|---|---|---|---|---|---|---|---|
| GDINO-tiny | **0.441** | **0.794** | 0.245 | 0.023 | 0.414 | 1.4–2.1 | 1486 |
| GDINO-base | 0.416 | 0.582 | **0.439** | 0.019 | **0.523** | 1.89 | 1722 |
| MM-GDINO-tiny | 0.006 | 0.000 | 0.000 | 0.000 | 0.000 | — | — |
| MM-GDINO-base | 0.337 | 0.428 | 0.360 | 0.001 | 0.027 | 1.4–1.7 | 1722 |
| YOLOE-26l | 0.358 | 0.629 | 0.091 | 0.000 | 0.000 | **9–14** | **318** |

**Hallazgos clave:**
- MM-GDINO-tiny descartado: bboxes degeneradas (bug en adaptador mmgdino).
- bare_head E1 universalmente débil (AP máx 0.023) → estrategia E2 necesaria para CR-01.
- GDINO-tiny y GDINO-base son los candidatos viables para fases posteriores.
- YOLOE-26l: única opción real-time viable, pero vest≈0 y bare_head=0 en zero-shot.

## Próximo hito

- **Task 4.3 (pendiente):** Auditoría manual del GT — inspección visual de ≥ 20 imágenes del BENCH para verificar precisión ≥ 95 % del `has_helmet` asignado por `center_in_bbox`.
- **Sprint 3:** Implementar estrategia E2 para CR-01 (inferir ausencia de casco desde matching persona/helmet) con GDINO-tiny y GDINO-base como candidatos principales.

## Vistas deprecadas (v1 — no usar)

- `canonical_cr01_cr02`: reemplazada por `canonical_v2`.
- `finetuning_cr01_cr02`: reemplazada por splits v2.

Los scripts que las generan (`generate_cr01_cr02_views.py`, `generate_finetuning_cr01_cr02.py`) tienen `sys.exit()` guard y están marcados DEPRECATED.
