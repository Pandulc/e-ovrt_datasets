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

> **Ojo — dos GT, dejá claro cuál es cuál.** La tabla de abajo describe el GT
> **histórico** (`person_gt.json`, 196 imgs, 340 personas / 111 violadoras), hoy
> **prohibido para evaluación** por contaminación de dominio (ver `bench_v3.md` y
> `curation_bench_obra.md`). El GT que se audita en esta Task 4.3 es el **curado**:
> `datasets/processed/coco/bench/curated/person_gt_bench_obra.json` —
> **147 imgs, 262 personas, 60 violadoras CR-01, 202 conformes** (regenerado sobre
> el núcleo curado bench_obra).

Histórico (196 imgs, `person_gt.json` — solo referencia, NO auditar ni evaluar):

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
Se evalúa sobre el GT **curado** vigente (`curated/person_gt_bench_obra.json`,
147 imgs / 262 personas); los conteos del histórico quedan entre paréntesis solo
como referencia:

- [x] CR-01 conformes: 202 ≥ 150 ✓ (histórico: 229)
- [ ] CR-01 violadoras: **60 < 150** — no alcanza el mínimo, y la curación
  **agrava** la limitación estructural: al excluir las 49 imágenes fuera de
  dominio se pierden 51 violadoras (histórico: 111 < 150, ya insuficiente)
- [ ] CR-02: GT no disponible en canonical_v2 (limitación metodológica)

## 3. Muestra de auditoría manual

**Decisión (2026-07-29):** la muestra sale de las **147 imágenes curadas** de
bench_obra, no de las 196 originales, y el GT auditado es
`datasets/processed/coco/bench/curated/person_gt_bench_obra.json` (262 personas,
60 violadoras CR-01). Auditar las 49 imágenes excluidas no aporta: ya están
documentadas como contaminación de dominio en `curation_bench_obra.md`
(auditoría docs/operacion/63).

**Kit de auditoría** — generado con `datasets/scripts/bench/build_audit_kit.py`
(muestreo determinista, `seed=43`):

- Universo: 104 imágenes curadas con ≥ 1 persona (29 con ≥ 1 violadora CR-01,
  75 solo conformes).
- Muestra: **24 imágenes = 12 con ≥ 1 violadora + 12 solo conformes** (~16 % de
  147) — cubre ambos sentidos del error (falso `sin casco` y falso `con casco`).
- Salida: `datasets/processed/audit_task43/` (gitignorado, regenerable) — PNGs
  numerados `01_…`–`24_…` con el GT dibujado encima (**verde** = persona
  `con casco`, **rojo** = persona `sin casco`, **ámbar** = `bare_head` del COCO
  curado), más `README.md` con las instrucciones y `sample_manifest.json` con la
  trazabilidad de la muestra.

```bash
python3 datasets/scripts/bench/build_audit_kit.py   # regenera el kit (determinista)
```

Para cada imagen: verificar que el rótulo con/sin casco de cada persona coincide
con la inspección visual y registrar ✓/✗ en la tabla §4.

## 4. Checklist por imagen

Para cada imagen auditada, registrar (los `imagen_id` corresponden a los PNG de
`datasets/processed/audit_task43/`; `has_helmet_gt` viene pre-cargado del GT curado):

| imagen_id | has_helmet_gt | has_helmet_visual | correcto | observaciones |
|---|---|---|---|---|
| 01_youtube-255_jpg.rf.c5a9f8ed208cb72e1a700ba52dc2fdfa | 1 persona: 1 con casco | | | |
| 02_youtube-237_jpg.rf.d07a927721fe259757237c3706ea22e5 | 2 personas: 2 con casco | | | |
| 03_ppe_0018_jpg.rf.be66fabcc8627f60d963454b5a227095 | 2 personas: 2 con casco | | | |
| 04_0_jpg.rf.2ff49f74309118f169e07aa12564df87 | 5 personas: 5 con casco | | | |
| 05_youtube-118_jpg.rf.9dc8b46dfbac73d9e4f983964355d7ac | 1 persona: 1 con casco | | | |
| 06_construction-823-_jpg.rf.640d8abfc7c7689d4a19e6aa00ac8984 | 1 persona: 1 con casco | | | |
| 07_class1_267_jpg.rf.ab7a08d97aba5b0748e976df6e65700a | 2 personas: 1 con casco, 1 sin casco | | | |
| 08_004063_jpg.rf.1b7cdc4035bcb24ef69b8798b444053e | 6 personas: 5 con casco, 1 sin casco | | | |
| 09_1125_jpg.rf.2958d0a57630bdde8c3b5c6c560152af | 6 personas: 6 sin casco | | | |
| 10_construction-3-_mp4-21_jpg.rf.4fc9ff5afc8387b5c673a424781c527c | 1 persona: 1 sin casco | | | |
| 11_youtube-388_jpg.rf.18caa1da4f818a65f73e48463cb2270e | 1 persona: 1 con casco | | | |
| 12_img_08_jpg.rf.0f132a9c7ca6d12a8a9d1c4b3dbd54da | 1 persona: 1 sin casco | | | |
| 13_777_jpg.rf.92dc6945342410ced7ac93f3dfbff0c5 | 2 personas: 2 sin casco | | | |
| 14_youtube-126_jpg.rf.786824e90daf3276130ca73ca610a8da | 2 personas: 2 sin casco | | | |
| 15_youtube-192_jpg.rf.93bea040de8cd55f34ffb12f6ffe30b1 | 1 persona: 1 sin casco | | | |
| 16_ppe_0064_jpg.rf.f019b082d09af2750a81ef5ea3fcbc3e | 1 persona: 1 con casco | | | |
| 17_class1_150_jpg.rf.5995dce34d38deb9eb0b6e36cae78f17 | 2 personas: 1 con casco, 1 sin casco | | | |
| 18_youtube-108_jpg.rf.9dc7ed5f816f07d520f3dbfaad08d40f | 2 personas: 2 con casco | | | |
| 19_youtube-455_jpg.rf.35acd2e91608806a26f3ac4e784ea512 | 2 personas: 2 con casco | | | |
| 20_class2_131_jpg.rf.ad8314a9273471f1280ce8789ea75376 | 1 persona: 1 sin casco | | | |
| 21_youtube-617_jpg.rf.309ef116f1d9074886d61bb0816b6b9e | 2 personas: 2 con casco | | | |
| 22_youtube-70_jpg.rf.2d5f69c78f062dfc572ccb6ce6bc3c9b | 2 personas: 2 con casco | | | |
| 23_00596_jpg.rf.d030c5d98b937d080d75db1c1b269a84 | 5 personas: 2 con casco, 3 sin casco | | | |
| 24_ppe_0355_jpg.rf.508753d5b708536eca53de192b927c61 | 4 personas: 2 con casco, 2 sin casco | | | |

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

- **CR-01 violadoras < 150**: v27 tiene train muy augmentado (Roboflow) pero val+test relativamente pequeños. En el GT curado vigente (`person_gt_bench_obra.json`) quedan **60 violadoras** — la curación de dominio **agrava** la limitación estructural respecto del histórico (111, ya < 150): al sacar las imágenes fuera de dominio se pierden 51 violadoras. Limitación del dataset, no del pipeline.
- **CR-02 GT ausente**: `NO-Safety Vest` no es clase de detección canonical_v2. `has_vest=False` requeriría raw annotations o un dataset con negativos explícitos de chaleco. Documentado como limitación metodológica; CR-02 queda pendiente de dataset complementario.
- **Criterio center_in_bbox**: usado en lugar de IoU. El centro del bbox `bare_head` debe caer dentro del `head_region` (tercio superior del bbox persona). Match rate observada: ~98 % (108/110 bare_head matchearon a una persona).
- **Leakage verificado**: los 196 stems del BENCH no aparecen en TRAIN (fix aplicado en `build_role_views.py`).
