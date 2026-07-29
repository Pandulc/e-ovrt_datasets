# Conversion Report

Conversor: `datasets/scripts/convert/convert_datasets.py`

## Vista canonical_v2 (activa — v2)

Clases de detección: `person`, `helmet`, `vest`, `bare_head`  
Fecha: 2026-06-18

| Dataset | Splits (imgs) | Anotaciones por clase | Estado |
|---|---|---|---|
| construction_site_safety | train=2603 / val=114 / test=82 | bare_head=2428, helmet=3551, person=10031, vest=3258 | convertido ✓ |
| ppe_siabar | train=1120 / val=326 / test=161 | helmet=1386, person=1442, vest=1944 | convertido ✓ |
| chv | train=1064 / val=133 / test=133 | helmet=3538, person=3887, vest=1784 | convertido ✓ |
| construction_safety_hardhat | — | — | no disponible (URL inválida) |

Comando:
```bash
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety ppe_siabar chv \
    --views canonical_v2
```

## Manifests de rol (datasets/splits/v2/)

| Rol | Imágenes | bare_head | helmet | vest | person |
|---|---:|---:|---:|---:|---:|
| TRAIN | 5540 | 2318 | 8286 | 6884 | 17020 |
| BENCH | 196 | 110 | 189 | 102 | 340 |
| DEMO | 1064 | 0 | 2762 | 1396 | 3050 |

- **TRAIN**: train split de construction_site_safety + todos los splits de chv y ppe_siabar  
- **BENCH**: val+test de construction_site_safety (BENCH excluido de TRAIN — sin fuga ✓)  
- **DEMO**: train de chv (calidad_defectos_pct=0)

vest y bare_head en BENCH por debajo de 150 (102 y 110 resp.) — limitación estructural del dataset v27 (train muy augmentado). Documentado en `bench_gt_audit.md`.

## GT persona-nivel del BENCH

Archivo: `datasets/processed/coco/bench/person_gt.json` (HISTÓRICO — prohibido para evaluación, ver registry/bench_v3.md; vigente: curated/person_gt_bench_obra.json)  
Criterio de asignación: center_in_bbox (centro del bbox violation dentro de la región de referencia)

| Métrica | Valor |
|---|---|
| Total personas | 340 |
| CR-01 violadoras (`has_helmet=False`) | 111 |
| CR-01 conformes (`has_helmet=True`) | 229 |
| CR-02 violadoras (`has_vest=False`) | 0 (*) |

(*) NO-Safety Vest no es clase canonical_v2 → CR-02 GT requiere raw annotations. Limitación documentada.

## Vistas deprecadas (v1 — no regenerar)

- `canonical_cr01_cr02`: DEPRECATED
- `finetuning_cr01_cr02`: DEPRECATED

## Resumen v1 (histórico)

| Dataset | Vista | Imágenes | Anotaciones |
|---|---|---:|---:|
| CHV | canonical_cr01_cr02 | 1330 | 9209 |
| SHEL5K | canonical_cr01_cr02 | 5000 | 75578 |
| Construction-PPE | canonical_cr01_cr02 | 1416 | 6082 |
| SH17 | canonical_cr01_cr02 | 8099 | 36194 |

## Notas de formato

- COCO: `bbox` en `[x, y, width, height]`.
- YOLO: `class_id x_center y_center width height`, normalizado a `[0, 1]`.
- ODVG: JSONL, una imagen por línea; `bbox` en `[x1, y1, x2, y2]`.
