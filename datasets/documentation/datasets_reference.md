# Datasets v2 — Referencia Técnica

Fecha de corte: 2026-06-18  
Versión del vocabulario: **canonical_v2** (`person`, `helmet`, `vest`, `bare_head`)

Documentación técnica de los cuatro datasets seleccionados para E-OVRT-VDP v2. Para el proceso de selección ver [`2026-06-18-metodologia-seleccion.md`](2026-06-18-metodologia-seleccion.md) y `datasets/registry/selection_scoring.csv`.

> Los datasets v1 (SH17, Construction-PPE, vocabulario `no_helmet`/`no_vest`) están en `legacy/documentation/`. No usar para el pipeline activo. **SHEL5K es la excepción: ES activo** — reingresó en 2026-07 como estrato de bench_v3 (5.000 imgs) y fuente canonical_v2 (la nota vieja de "no usar" era de la era v1). Ver `datasets/registry/bench_v3.md`.
>
> ✎ 2026-08-19: las asignaciones de ROL (TRAIN/BENCH/DEMO) que aparecen por dataset en este documento son **históricas** — los roles fueron archivados el 2026-08-15 (ver `datasets/splits/DEPRECATED.md`). El benchmark vigente es `bench_v3` (sección al final).

---

## 1. Construction Site Safety v27

| Campo | Valor |
|---|---|
| **ID** | `construction_site_safety` |
| **Nombre completo** | Construction Site Safety (Roboflow Universe Projects) |
| **Fuente** | Roboflow Universe |
| **URL** | https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety |
| **Versión** | v27 (con augmentación Roboflow en el split train) |
| **Licencia** | CC BY 4.0 |
| **Formato raw** | YOLOv8 (exportación Roboflow) |
| **Descarga** | `datasets/scripts/download/download_construction_site_safety.sh` |

### Imágenes y splits

| Split | Imágenes |
|---|---:|
| train | 2 603 |
| val | 114 |
| test | 82 |
| **Total** | **2 799** |

### Clases originales

`Hardhat`, `Mask`, `NO-Hardhat`, `NO-Mask`, `NO-Safety Vest`, `Person`, `Safety Cone`, `Safety Vest`, `machinery`, `vehicle`

### Mapeo a canonical_v2

| Clase canónica | Clase(s) original(es) |
|---|---|
| `person` | `Person` |
| `helmet` | `Hardhat` |
| `vest` | `Safety Vest` |
| `bare_head` | `NO-Hardhat` |

`NO-Safety Vest`, `Mask`, `NO-Mask`, `Safety Cone`, `machinery`, `vehicle` → descartadas en canonical_v2.

### Anotaciones en canonical_v2

| Clase | Anotaciones (todos los splits) |
|---|---:|
| `person` | 10 031 |
| `helmet` | 3 551 |
| `vest` | 3 258 |
| `bare_head` | 2 428 |

### Rol en el pipeline (histórico — roles archivados 2026-08-15)

| Rol | Splits usados |
|---|---|
| **TRAIN** | train |
| **BENCH** | val + test (196 imgs en total) |

El dataset fue la única fuente del BENCH histórico de 196 imgs (340 personas, 111 violadoras CR-01) — **superado por bench_v3**; su derivado curado (`bench_obra`) es hoy uno de los 3 estratos.

### Estructura raw

```text
datasets/raw/construction_site_safety/
  construction-site-safety-v27-yolov8.zip   # archivo descargado (150 MB)
  data.yaml                                  # clases y rutas de split
  train/
    images/                                  # 2 603 imágenes .jpg
    labels/                                  # 2 603 archivos .txt (YOLOv8)
  valid/
    images/                                  # 114 imágenes
    labels/
  test/
    images/                                  # 82 imágenes
    labels/
```

### Particularidades

- **Augmentación**: el split `train` está augmentado por Roboflow (recortes, flips, cambios de color). Las imágenes de val y test son sin augmentar → BENCH sin sesgo por augmentación.
- **CR-02 limitado**: `NO-Safety Vest` existe en el raw pero **no** se incluyó en canonical_v2. El GT de persona-nivel (person_gt.json — HISTÓRICO, prohibido para evaluación, ver registry/bench_v3.md; vigente: curated/person_gt_bench_obra.json) tiene `has_vest=False` para 0 personas → CR-02 no evaluable con este dataset.
- **bare_head anotado**: única fuente del corpus con anotaciones directas de cabeza descubierta (NO-Hardhat), lo que hace viable la estrategia E1 de detección directa.

---

## 2. CHV — Color Helmet and Vest

| Campo | Valor |
|---|---|
| **ID** | `chv` |
| **Nombre completo** | CHV: Color Helmet and Vest Dataset |
| **Fuente** | GitHub (ZijianWang-ZW/PPE_detection) |
| **URL** | https://github.com/ZijianWang-ZW/PPE_detection |
| **Versión** | única (sin versiones, descarga directa) |
| **Licencia** | Open/free use per repository; verificar términos de redistribución |
| **Formato raw** | YOLO (propio del repositorio) |
| **Descarga** | `datasets/scripts/download/download_chv.sh` |

### Imágenes y splits

| Split | Imágenes |
|---|---:|
| train | 1 064 |
| val | 133 |
| test | 133 |
| **Total** | **1 330** |

### Clases originales

`person`, `vest`, `blue helmet`, `red helmet`, `white helmet`, `yellow helmet`

Los cascos están segmentados por color. No existen clases de negación (sin casco, sin chaleco).

### Mapeo a canonical_v2

| Clase canónica | Clase(s) original(es) |
|---|---|
| `person` | `person` |
| `helmet` | `blue helmet`, `red helmet`, `white helmet`, `yellow helmet` |
| `vest` | `vest` |
| `bare_head` | — (ausente; no aporta) |

Los cuatro colores de casco se fusionan en una única clase `helmet`.

### Distribución de instancias en raw

| Clase original | Instancias |
|---|---:|
| `person` | 3 887 |
| `vest` | 1 784 |
| `blue helmet` | 508 |
| `red helmet` | 536 |
| `white helmet` | 1 195 |
| `yellow helmet` | 1 299 |
| **Total helmets** | **3 538** |

### Anotaciones en canonical_v2

| Clase | Anotaciones |
|---|---:|
| `person` | 3 887 |
| `helmet` | 3 538 |
| `vest` | 1 784 |
| `bare_head` | 0 |

### Rol en el pipeline (histórico — roles archivados 2026-08-15)

| Rol | Splits usados |
|---|---|
| **TRAIN** | val + test |
| **DEMO** | train (1 064 imgs) |

El train de CHV se reserva para DEMO porque sus imágenes tienen alta calidad visual (sin augmentación, variedad de colores, escenas reales de obra). El val y test aportan a TRAIN.

### Estructura raw

```text
datasets/raw/chv/
  CHV_dataset.zip            # archivo descargado (~420 MB)
  CHV_dataset/
    images/                  # 1 330 imágenes .jpg
    annotations/             # 1 330 archivos .txt (YOLO)
    data split/              # listas train.txt / val.txt / test.txt
```

### Particularidades

- **Sin negativas**: no tiene anotaciones de ausencia (bare_head, no_vest). Aporta presencia de EPP al TRAIN pero no aporta a la evaluación de riesgos CR-01/CR-02.
- **Calidad alta para DEMO**: imágenes de obra real sin augmentar, variedad de colores de casco (rol profesional visible), buena iluminación y resolución.
- **Split oficial preservado**: CHV tiene su propio train/val/test; se respeta esa partición. El split train va a DEMO, val+test van a TRAIN.

---

## 3. PPE-SIABAR — PPE Dataset for Workplace Safety

| Campo | Valor |
|---|---|
| **ID** | `ppe_siabar` |
| **Nombre completo** | PPE Dataset for Workplace Safety (SIABAR) |
| **Fuente** | Roboflow Universe (siabar) |
| **URL** | https://universe.roboflow.com/siabar/ppe-dataset-for-workplace-safety |
| **Versión** | v1 |
| **Licencia** | CC BY 4.0 |
| **Formato raw** | YOLOv8 (exportación Roboflow) |
| **Descarga** | `datasets/scripts/download/download_ppe_siabar.sh` |

### Imágenes y splits

| Split | Imágenes |
|---|---:|
| train | 1 120 |
| val | 326 |
| test | 161 |
| **Total** | **1 607** |

### Clases originales

`Boots`, `Helmet`, `Person`, `Vest`

No tiene clases de negación. `Boots` se descarta en canonical_v2.

### Mapeo a canonical_v2

| Clase canónica | Clase(s) original(es) |
|---|---|
| `person` | `Person` |
| `helmet` | `Helmet` |
| `vest` | `Vest` |
| `bare_head` | — (ausente) |

### Anotaciones en canonical_v2

| Clase | Anotaciones (todos los splits) |
|---|---:|
| `person` | 1 442 |
| `helmet` | 1 386 |
| `vest` | 1 944 |
| `bare_head` | 0 |

### Rol en el pipeline (histórico — roles archivados 2026-08-15)

| Rol | Splits usados |
|---|---|
| **TRAIN** | train + val + test (todos) |

Todo el dataset aportaba a TRAIN. No formó parte de BENCH ni DEMO.

### Estructura raw

```text
datasets/raw/ppe_siabar/
  ppe-dataset-for-workplace-safety-v1-yolov8.zip   # archivo descargado (~98 MB)
  data.yaml
  train/
    images/                                          # 1 120 imágenes
    labels/
  valid/
    images/                                          # 326 imágenes
    labels/
  test/
    images/                                          # 161 imágenes
    labels/
```

### Particularidades

- **Alta cobertura de vest**: ratio vest/persona alto (1 944 / 1 442), útil para reforzar el reconocimiento de chaleco en TRAIN.
- **Sin bare_head**: no aporta a estrategias E1/E3 de detección de ausencia de casco.
- **Dominio workplace**: incluye ambientes de manufactura e interior además de obra civil. Agrega diversidad de contexto al TRAIN.

---

## 4. Construction Safety Hardhat — DESCARTADO

| Campo | Valor |
|---|---|
| **ID** | `construction_safety_hardhat` |
| **Nombre completo** | Construction Safety Image Classification System (Kaggle) |
| **Fuente** | Kaggle (muhammetzualli) |
| **URL** | https://www.kaggle.com/datasets/muhammetzualli/construction-safety-image-classification-system |
| **Licencia** | CC0 (Public Domain) |
| **Estado** | **DESCARTADO — URL inválida al 2026-06-18** |

### Clases originales previstas

`helmet`, `no-helmet`, `vest`, `harness`, `person`

### Razón del descarte

El dataset aparecía como candidato prioritario por tener `no-helmet` explícito (equivalente de bare_head). Sin embargo, la URL de descarga de Kaggle devolvió error 404 al intentar la descarga. El dataset no estaba disponible en la plataforma al momento de la ejecución del pipeline v2.

### Impacto

- **TRAIN** corre con los tres datasets restantes (5 540 imágenes total).
- La ausencia de este dataset no compromete la evaluación BENCH (que ya tiene bare_head desde construction_site_safety).
- Si el dataset vuelve a estar disponible, el script `legacy/scripts/download/download_construction_safety_hardhat.py` ya existe (archivado) y está listo para usarlo.

---

## Resumen del corpus v2

> ✎ Las columnas/tablas de rol de abajo son HISTÓRICAS (roles archivados 2026-08-15) y
> "BENCH = 196" está SUPERADO por bench_v3 — nunca citarlo como benchmark vigente.

| Dataset | Imágenes | Rol(es) (histórico) | bare_head | Licencia |
|---|---:|---|:---:|---|
| construction_site_safety v27 | 2 799 | TRAIN + BENCH | ✓ | CC BY 4.0 |
| chv | 1 330 | TRAIN + DEMO | ✗ | Open (ver repo) |
| ppe_siabar v1 | 1 607 | TRAIN | ✗ | CC BY 4.0 |
| shel5k | 5 000 | — (posterior a los roles; estrato de bench_v3) | ✓ (GT nativo vía `head`) | CC BY 4.0 |
| construction_safety_hardhat | — | — (descartado) | ✓ | CC0 |

| Rol (histórico) | Imágenes | Fuente |
|---|---:|---|
| **TRAIN** | 5 540 | css-train + chv-val/test + ppe_siabar-all |
| **BENCH** | 196 | css-val + css-test |
| **DEMO** | 1 064 | chv-train |

---

## Benchmark vigente: `bench_v3` (2026-07-23)

Benchmark de imágenes oficial: **6.477 imágenes estratificadas en 3 fuentes
independientes**, cada imagen etiquetada con su `stratum`:

| Estrato | Imágenes | Nota |
|---|---:|---|
| `bench_obra` | 147 (62 test + 85 val) | núcleo curado del BENCH histórico, verificado visualmente |
| `chv` | 1 330 | mejor AP de `vest` medido |
| `shel5k` | 5 000 | Mendeley CC BY 4.0; GT nativo de `bare_head` (clase `head`) + `person_gt_shel5k.json` para atributos CR-01 |

- Archivo congelado: `datasets/processed/coco/bench/curated/bench_v3.json`; el manifest
  (`bench_v3_manifest.json`) lleva sha256 por fuente para verificación del freeze.
- Se construye con `datasets/scripts/curate/build_bench_v3.py` (idempotente, TDD).
- Provenance y salvedades por estrato: `datasets/registry/bench_v3.md`.
- **Reportar métricas por estrato Y agregadas — nunca solo el agregado.**
