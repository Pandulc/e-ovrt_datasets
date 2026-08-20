# Estructura del Repositorio — e-ovrt_datasets

Fecha de corte: 2026-06-18

Descripción completa de la organización de directorios y archivos del repositorio, con el rol de cada componente en el pipeline de datos.

---

## Árbol general

```text
e-ovrt_datasets/
├── README.md                          # Entrada principal: comandos, datasets, política
├── legacy/                            # Artefactos v1 pre-2026-06-17 (no usar)
│   ├── README.md
│   ├── documentation/                 # Docs v1 archivadas
│   ├── scripts/                       # Scripts v1 obsoletos
│   ├── plans/                         # Plan de implementación ejecutado (histórico)
│   └── splits/cr01_cr02/             # Manifests v1 (vocabulario no_helmet/no_vest)
│
└── datasets/
    ├── documentation/                 # Documentación activa (este directorio)
    ├── registry/                      # Metadata, licencias, contratos, reportes
    ├── raw/                           # Imágenes y archivos descargados (gitignored)
    ├── processed/                     # Outputs del conversor (parcialmente gitignored)
    ├── scripts/                       # Pipeline de scripts por etapa
    ├── splits/                        # DEPRECADO ENTERO (v2/ archivado en legacy/ el 2026-08-15)
    └── tests/                         # Suite pytest (sin dependencias de datos raw)
```

---

## `datasets/documentation/` — Documentación activa

| Archivo | Rol |
|---|---|
| `README.md` | Índice de toda la documentación activa con tabla de contenidos. |
| `estado_avance.md` | Estado actual por fase, dataset y sprint experimental. Leer primero. |
| `datasets_reference.md` | Referencia técnica completa de los 4 datasets v2: estructura raw, clases, mapeo, rol. |
| `guia_conversiones.md` | Formatos generados (COCO, YOLO, ODVG), rutas de salida y comandos. |
| `estructura-repositorio.md` | Este documento. |
| `investigacion-roboflow-universe.md` | Investigación de candidatos en Roboflow Universe evaluados para v2. |
| `2026-06-17-reinicio-seleccion-datasets-design.md` | Documento de diseño base v2: vocabulario, vistas, contrato de anotación, criterios. |
| `2026-06-18-metodologia-seleccion.md` | Procedimiento operativo para armar TRAIN y BENCH. |
| `2026-06-18-protocolo-experimental-ausencia.md` | Criterios de medición para CR-01/CR-02 en experimentos. |

---

## `datasets/registry/` — Fuente de verdad de metadata

Archivos de provenance, licencias y reportes que documentan el estado del corpus. No se modifican manualmente; se actualizan por scripts o auditorías.

| Archivo | Contenido |
|---|---|
| `datasets_metadata.yaml` | Registro principal: versión, rol, estado, splits, clases, SHA256, notas de cada dataset. |
| `annotation_contract_v2.yaml` | Contrato formal de anotación v2: qué se anota, criterios por clase, casos límite. |
| `class_mapping.yaml` | Mapeo detallado clases originales → canonical_v2 por dataset. Fuente de verdad del conversor. |
| `conversion_report.md` | Reporte de conversión: conteos por dataset/split/clase tras ejecutar `convert_datasets.py`. |
| `bench_gt_audit.md` | Auditoría del GT persona-nivel del BENCH (Task 4.3 ya ejecutada — kit en `datasets/processed/audit_task43/`). |
| `bench_v3.md` | **Benchmark de imágenes vigente**: bench_v3 (6.477 imgs, 3 estratos) — provenance, salvedades y freeze sha256. |
| `clip_bench.md` | Banco de clips de video: composición, GT temporal, manifest. |
| `curation_bench_obra.md` | Curado del núcleo `bench_obra` (147 imgs). |
| `evaluation_ppe_dataset.md` | Evaluación del candidato `ppe-dataset` (rbyz) — rechazado S0. |
| `plantilla-consentimiento-audiovisual.md` | Plantilla de consentimiento para el material de rodaje propio. |
| `download_log.md` | Log de descargas: fechas, fuentes, checksums, observaciones. |
| `license_registry.md` | Licencias por dataset, material de video y pesos de modelo. |
| `selection_scoring.csv` | Scoring multicriteria de candidatos v2 para justificar la selección. |

---

## `datasets/raw/` — Datos descargados (gitignored)

Archivos de imagen, archivos ZIP y anotaciones tal como los provee cada fuente. No se modifican.

```text
datasets/raw/
├── construction_site_safety/
│   ├── construction-site-safety-v27-yolov8.zip   # 150 MB
│   ├── data.yaml
│   ├── train/images/ + labels/                   # 2 603 imgs (YOLOv8)
│   ├── valid/images/ + labels/                   # 114 imgs
│   └── test/images/ + labels/                    # 82 imgs
│
├── chv/
│   ├── CHV_dataset.zip                           # ~420 MB
│   └── CHV_dataset/
│       ├── images/                               # 1 330 imgs
│       ├── annotations/                          # 1 330 .txt (YOLO)
│       └── data split/                          # train.txt / val.txt / test.txt
│
├── ppe_siabar/
│   ├── ppe-dataset-for-workplace-safety-v1-yolov8.zip   # ~98 MB
│   ├── data.yaml
│   ├── train/images/ + labels/                  # 1 120 imgs
│   ├── valid/images/ + labels/                  # 326 imgs
│   └── test/images/ + labels/                   # 161 imgs
│
├── shel5k/
│   └── 9rcv8mm682-4/Safety Helmet Wearing Dataset/
│       ├── Images/                               # 5 000 imgs (PNG)
│       └── Annotations/                          # 5 000 XML (Pascal VOC) — versionados
│
├── MOCS/                                         # copia Roboflow (1 471 imgs, solo Worker) — piloto A1; gitignored entero
│
├── clip_bench/                                   # videos fuente del banco de clips (rodaje + lote de internet) — gitignored
│
└── coco_val2017/                                 # 5 000 imgs COCO val2017 (arnés de retención OV del tier T2) — gitignored entero
```

> Nota: `construction_safety_hardhat/` ya no existe en disco (dataset descartado
> 2026-06-17 por URL inválida; nunca se descargó).

---

## `datasets/processed/` — Outputs del conversor

Generados por `convert_datasets.py`. Las imágenes raw no se copian aquí; los formatos referencian paths relativos al raw o son self-contained en ODVG.

```text
datasets/processed/
├── coco/
│   ├── canonical_v2/
│   │   ├── construction_site_safety/
│   │   │   ├── train.json      # COCO por split
│   │   │   ├── val.json
│   │   │   └── test.json
│   │   ├── chv/
│   │   │   ├── train.json
│   │   │   ├── val.json
│   │   │   └── test.json
│   │   ├── ppe_siabar/
│   │   │   ├── train.json
│   │   │   ├── val.json
│   │   │   └── test.json
│   │   └── shel5k/
│   │       ├── train.json
│   │       ├── val.json
│   │       └── test.json
│   └── bench/                                   # BENCH GT — versionado en git
│       ├── construction_site_safety_bench.json  # COCO unificado val+test (196 imgs) (HISTÓRICO — prohibido para evaluación, ver registry/bench_v3.md)
│       ├── person_gt.json                       # GT persona-nivel (340 personas) (HISTÓRICO — prohibido para evaluación, ver registry/bench_v3.md; vigente: curated/person_gt_bench_obra.json)
│       └── curated/                             # bench curado VIGENTE: bench_obra val/test, person_gt_bench_obra.json, bench_v3.json
│
├── yolo/
│   └── canonical_v2/                            # Mismo layout por dataset/split
│
└── odvg/
    └── canonical_v2/                            # JSONL por split
```

**Política de versionado**: solo `datasets/processed/coco/bench/` está versionado en git (BENCH GT necesario para reproducibilidad). El resto es regenerable con `convert_datasets.py`.

---

## `datasets/scripts/` — Pipeline por etapa

Cada subdirectorio agrupa los scripts de una etapa del pipeline. Los scripts resuelven paths desde la raíz del repo (`Path(__file__).resolve().parents[N]`); ejecutar desde cualquier directorio.

### `scripts/download/` — Descarga de fuentes

| Script | Dataset |
|---|---|
| `download_construction_site_safety.sh` | Construction Site Safety v27 (Roboflow, requiere `ROBOFLOW_API_KEY`) |
| `download_ppe_siabar.sh` | PPE-SIABAR v1 (Roboflow, requiere `ROBOFLOW_API_KEY`) |
| `download_chv.sh` | CHV (Google Drive, sin API key) |
| `download_shel5k.sh` | SHEL5K (Mendeley Data, sin API key) — volvió de `legacy/` el 2026-08-19: SHEL5K es fuente canonical_v2 y estrato de bench_v3 |
| `README.md` | Instrucciones y requisitos por script |

(`download_construction_safety_hardhat.py` está en `legacy/scripts/download/` — dataset descartado 2026-06-17, URL de Kaggle inválida.)

### `scripts/validate/` — Validación básica

| Script | Función |
|---|---|
| `summarize_raw_dataset.sh` | Cuenta imágenes y labels por split; verifica paridad imagen↔label. |

### `scripts/convert/` — Conversión a canonical_v2

| Script | Función |
|---|---|
| `convert_datasets.py` | Convierte raw → COCO + YOLO + ODVG para la vista `canonical_v2`. Acepta `--datasets` y `--views` como argumentos. La función `configs()` interna es la fuente de verdad para agregar datasets. |

```bash
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety chv ppe_siabar shel5k \
    --views canonical_v2
```

### `scripts/curate/` — Curado del benchmark

| Script | Función |
|---|---|
| `build_bench_v3.py` | Construye `bench_v3.json` (benchmark vigente: 6.477 imgs, 3 estratos) desde las 4 fuentes curadas. Idempotente; TDD (`tests/test_bench_v3*.py`). |
| `build_bench_obra.py` | Construye el núcleo curado `bench_obra` (147 imgs) desde el BENCH histórico auditado. |
| `bench_v3_report.py` | Reporte de métricas sobre bench_v3, por estrato y agregado. |
| `leakage_check.py` | Verifica que no haya imágenes del BENCH en el TRAIN (chequeo de fuga). |
| ~~`build_role_views.py`~~ | **ARCHIVADO 2026-08-15** en `legacy/scripts/curate/`. Generaba `splits/v2/{train,bench,demo}.txt`: los tres roles estaban huérfanos y cada uno fue superado (BENCH→`bench_v3`, TRAIN→`finetuning_v1`, DEMO→catálogo del media-plane, que apunta al raw). Ver `datasets/splits/DEPRECATED.md`. |

### `scripts/selection/` — Herramienta de muestreo de calidad

| Script | Función |
|---|---|
| `quality_sample.py` | Muestrea imágenes de candidatos para evaluación visual de calidad durante la selección. |

### `scripts/bench/` — Construcción y evaluación del BENCH

| Script | Función |
|---|---|
| `geometry.py` | Helpers de geometría: IoU, head_region, center_in_bbox para asignación de annotations. |
| `build_person_gt.py` | Construye `person_gt.json` (HISTÓRICO — prohibido para evaluación, ver registry/bench_v3.md; vigente: curated/person_gt_bench_obra.json) con atributos `has_helmet`/`has_vest` por persona en el BENCH. |
| `evaluate_bench.py` | Evalúa un `detections.jsonl` de e-ovrt_media-plane contra el GT del BENCH: AP@50 por clase y recall CR-01. |

```bash
# Evaluar una corrida del media-plane (par CURADO — el único válido)
python3 datasets/scripts/bench/evaluate_bench.py \
    --detections ../e-ovrt_media-plane/runs/<run_id>/detections.jsonl \
    --bench-coco datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_val.json \
    --person-gt datasets/processed/coco/bench/curated/person_gt_bench_obra.json
# (el split test se evalúa igual con construction_site_safety_bench_obra_test.json)
```

> **Nota:** el par histórico `construction_site_safety_bench.json` + `person_gt.json`
> está **prohibido para evaluación** (bench contaminado de dominio, 196 imgs /
> 111 violadoras — ver `registry/bench_v3.md`); evaluar siempre con los COCO
> curados de `curated/` + `person_gt_bench_obra.json`.

### `scripts/videogt/` — GT de video (video-gt-lab, spec 43)

| Script | Función |
|---|---|
| `prepare_clip.sh` | Etapa 0: normaliza un video fuente a CFR sin audio (ffmpeg) y emite `<clip_id>.info.json`; todo lo que entra a CVAT pasa por acá. |
| `split_cvat_project.py` | Divide un export CVAT a nivel PROYECTO en un XML por task (etapa 2b; sin él, el GT sale negativo en silencio). |
| `cvat_xml.py` | Parser del formato "CVAT for video 1.1": tracks con visibilidad y atributos mutables por frame. |
| `cvat_labels.json` | Definición de labels para los proyectos CVAT del banco. |
| `derive_clip_gt.py` | Derivación determinística de `clip_gt.v2` (episodios CR-01/CR-02) desde el XML de CVAT corregido. |
| `apply_adjudications.py` | Aplica adjudicaciones humanas de huecos `unknown` sobre el XML corregido (F-GT1). |
| `apply_attribute_corrections.py` | Aplica correcciones de atributos explícitos declaradas en `clip.yaml`. |
| `compare_annotations.py` | Compara dos `clip_gt.v2` del mismo clip (doble anotación): kappa de Cohen por ventana + deltas de episodios. |

(`gen_ficha.py` fue archivado en `legacy/scripts/videogt/` el 2026-08-19 — sin referencias en ningún pipeline ni doc.)

---

## ~~`datasets/splits/v2/`~~ — ARCHIVADO 2026-08-15 en `legacy/splits/v2/`

> Los tamaños de abajo se conservan **como referencia histórica**. **Nunca citar "el BENCH
> de 196 imágenes" como benchmark de un resultado** — todo resultado reportable usa
> `bench_v3` (6.477 imgs). Constancia y tabla de supersesión: `datasets/splits/DEPRECATED.md`.

| Archivo | Contenido |
|---|---|
| `train.txt` | Paths absolutos a imágenes de TRAIN (5 540 imgs). |
| `bench.txt` | Paths a imágenes de BENCH (196 imgs). |
| `demo.txt` | Paths a imágenes de DEMO (1 064 imgs). |
| `manifest.json` | Conteos por rol y por clase; metadatos de generación. |

Los manifests son la fuente de verdad para la asignación de imágenes a cada rol. Los configs de dataset en `e-ovrt_media-plane/configs/datasets/` referencian estas mismas imágenes vía paths relativos.

---

## `datasets/tests/` — Suite de tests

Tests unitarios y de integración. No dependen de datos raw; usan fixtures sintéticos en `conftest.py`.

| Archivo | Qué verifica |
|---|---|
| `test_geometry.py` | Helpers de geometría (IoU, head_region, center_in_bbox). |
| `test_person_gt.py` | Construcción correcta de atributos has_helmet/has_vest. |
| `test_contract.py` | Cumplimiento del contrato de anotación v2 por dataset. |
| `test_leakage.py` | Ausencia de fuga TRAIN↔BENCH. |
| `test_balance.py` | Conteos mínimos de clases por rol. |
| `test_bare_head_guard.py` | Que bare_head no se derive por resta (solo desde etiquetas explícitas). |
| `test_quality_sample.py` | Herramienta de muestreo. |
| `test_label_path.py` | Correcta resolución de paths label↔imagen. |

```bash
python3 -m pytest datasets/tests/ -q
```

---

## Flujo de datos completo

```
Fuentes externas (Roboflow, GitHub, Kaggle)
    │
    ▼  scripts/download/
datasets/raw/<dataset_id>/         # imágenes + anotaciones raw (gitignored)
    │
    ▼  scripts/validate/summarize_raw_dataset.sh
[verificación de integridad: paridad imgs↔labels]
    │
    ▼  scripts/convert/convert_datasets.py --views canonical_v2
datasets/processed/{coco,yolo,odvg}/canonical_v2/<dataset_id>/   # gitignored
    │
    ▼  [ARCHIVADO 2026-08-15 -> legacy/] scripts/curate/build_role_views.py
datasets/splits/v2/{train,bench,demo}.txt + manifest.json        # -> legacy/splits/v2/
    │
    ├──▶ e-ovrt_media-plane/configs/datasets/*.yaml               # TRAIN / DEMO
    │
    ▼  scripts/bench/build_person_gt.py
datasets/processed/coco/bench/person_gt.json                     # versionado (HISTÓRICO — prohibido para evaluación, ver registry/bench_v3.md; vigente: curated/person_gt_bench_obra.json)
    │
    ▼  e-ovrt_media-plane (corrida experimental)
runs/<run_id>/detections.jsonl
    │
    ▼  scripts/bench/evaluate_bench.py
[AP@50 por clase, recall CR-01, diagnóstico por modelo]
```

---

## Relación con e-ovrt_media-plane

Los dos repositorios deben estar como directorios hermanos:

```text
proyectos/
├── e-ovrt_datasets/      # este repo
└── e-ovrt_media-plane/   # pipeline de inferencia
```

Los configs de dataset en `e-ovrt_media-plane/configs/datasets/` usan paths relativos del tipo `../e-ovrt_datasets/datasets/raw/...`, resueltos desde el CWD al momento de ejecutar `eovrt-media run`. `ImageFolderSource` es no recursivo: los configs apuntan a un directorio hoja (e.g. `datasets/raw/chv/CHV_dataset/images/train`), no al raíz del dataset.
