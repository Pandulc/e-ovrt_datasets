# Auditoría del GT del BENCH — construction_site_safety

> **Task 4.3** — Checkpoint humano. Criterio de aprobación: precisión del GT ≥ 95 %.

## 1. Generación del GT

```bash
# Paso 1: descargar y convertir
ROBOFLOW_API_KEY=<key> bash datasets/scripts/download/download_construction_site_safety.sh
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety --views canonical_v2

# Paso 2: merge val+test → BENCH
python3 datasets/scripts/bench/build_bench_coco.py \
    --coco-val datasets/processed/coco/canonical_v2/construction_site_safety/val.json \
    --coco-test datasets/processed/coco/canonical_v2/construction_site_safety/test.json \
    --out datasets/processed/coco/bench/construction_site_safety_bench.json

# Paso 3: construir GT persona-nivel (center_in_bbox)
python3 datasets/scripts/bench/build_person_gt.py \
    --coco datasets/processed/coco/bench/construction_site_safety_bench.json \
    --out datasets/processed/coco/bench/person_gt.json
```

## 2. Conteos del GT generado

| Métrica | Valor |
|---|---|
| Imágenes BENCH | 196 (val=114 + test=82) |
| Total personas | 340 |
| CR-01 violadoras (`has_helmet=False`) | 111 |
| CR-01 conformes (`has_helmet=True`) | 229 |
| CR-02 violadoras (`has_vest=False`) | 0 * |
| CR-02 conformes (`has_vest=True`) | 340 * |

\* `NO-Safety Vest` no es clase canonical_v2 → `has_vest` derivado de raw annotations (ver §7).  
Criterio de asignación: `center_in_bbox` — el centro del bbox violation cae dentro de la región de referencia.

**Mínimo requerido (spec §8):** ≥ 150 violadoras + ≥ 150 conformes por condición.

- [x] CR-01 conformes: 229 ≥ 150 ✓
- [ ] CR-01 violadoras: **111 < 150** — no alcanza mínimo (limitación estructural v27)
- [ ] CR-02: GT no disponible en canonical_v2 (limitación metodológica)

## 3. Muestra de auditoría manual

Samplear ≥ 10 % del conjunto (≥ 20 imágenes de 196):

```bash
# Ver imágenes de val y test con sus anotaciones canonical_v2
# Comparar visualmente has_helmet del GT con la presencia/ausencia de casco
ls datasets/raw/construction_site_safety/valid/images | head -20
ls datasets/raw/construction_site_safety/test/images | head -20
```

Para cada imagen: verificar que `has_helmet` del GT coincide con la inspección visual
de las anotaciones `bare_head` del COCO canonical_v2.

## 4. Checklist por imagen

Para cada imagen auditada, registrar:

| imagen_id | has_helmet_gt | has_helmet_visual | correcto | observaciones |
|---|---|---|---|---|
| — | — | — | — | — |

## 5. Resumen de la auditoría

<!-- Completar tras la revisión manual -->

| Métrica | Valor |
|---|---|
| Imágenes auditadas | — |
| Imágenes con GT correcto | — |
| Precisión del GT | — % |
| Errores CR-01 encontrados | — |
| Errores CR-02 encontrados | — |

**Umbral de aprobación:** precisión ≥ 95 %.

- [ ] Precisión CR-01 ≥ 95 %
- [ ] CR-02: documentar limitación

## 6. Decisión

- [ ] **APROBADO** — GT válido para evaluación BENCH
- [ ] **RECHAZADO** — describir problema y corrección necesaria

**Auditado por:** _______________  
**Fecha:** _______________  
**Versión del dataset:** construction-site-safety v27 (Roboflow)

## 7. Observaciones metodológicas

- **CR-01 violadoras < 150**: v27 tiene train muy augmentado (Roboflow) pero val+test relativamente pequeños. 111 violadoras = limitación estructural del dataset, no del pipeline.
- **CR-02 GT ausente**: `NO-Safety Vest` no es clase de detección canonical_v2. `has_vest=False` requeriría raw annotations o un dataset con negativos explícitos de chaleco. Documentado como limitación metodológica; CR-02 queda pendiente de dataset complementario.
- **Criterio center_in_bbox**: usado en lugar de IoU. El centro del bbox `bare_head` debe caer dentro del `head_region` (tercio superior del bbox persona). Match rate observada: ~98 % (108/110 bare_head matchearon a una persona).
- **Leakage verificado**: los 196 stems del BENCH no aparecen en TRAIN (fix aplicado en `build_role_views.py`).
