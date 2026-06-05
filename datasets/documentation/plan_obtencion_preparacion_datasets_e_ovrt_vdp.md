# Plan de obtención y preparación de datasets — E-OVRT-VDP

> Documento operativo para comenzar la etapa de implementación asociada a obtención, verificación, normalización y partición de datasets.

## 1. Objetivo de esta etapa

Construir un corpus trazable, reproducible y usable para las primeras corridas del prototipo experimental E-OVRT-VDP, priorizando las condiciones de riesgo con mejor cobertura en datasets públicos:

- **CR-01 — Persona sin casco**
- **CR-02 — Persona sin chaleco reflectivo**

Estas dos condiciones deben tratarse como el **núcleo inicial** de obtención, preparación, evaluación baseline y eventual comparación con fine-tuning. Las condiciones CR-03, CR-04, CR-05 y CR-06 quedan como extensiones condicionadas por disponibilidad de datos, reglas espaciales, tracking, entorno controlado o anotación complementaria.

---

## 2. Orden propuesto de obtención

| Orden | Dataset | Prioridad | Uso previsto | Condiciones cubiertas | Estado operativo |
|---:|---|---|---|---|---|
| 1 | SH17 | Alta | Fine-tuning / evaluación EPP | CR-01 directa; CR-02 parcial | Descargar primero |
| 2 | SHEL5K | Alta | Evaluación y apoyo CR-01 | CR-01 directa | Descargar primero |
| 3 | CHV | Alta | Evaluación CR-01 / CR-02 en construcción | CR-01 y CR-02 directas | Descargar primero |
| 4 | Construction-PPE | Alta | Evaluación de incumplimiento EPP | CR-01 y CR-02 directas | Descargar primero |
| 5 | GDUT-HWD | Media-alta | Refuerzo CR-01 / color de casco | CR-01 directa | Descargar después de núcleo base |
| 6 | SHWD | Media-alta | Refuerzo CR-01 / casco vs no casco | CR-01 directa | Descargar después de núcleo base |
| 7 | SODA | Media | Contexto de obra / entidades auxiliares | Apoyo parcial CR-05 / CR-06 | Descargar para extensiones |
| 8 | Pictor-PPE | Condicionada | Cumplimiento casco/chaleco | CR-01 y CR-02 directas | Verificar licencia y disponibilidad efectiva |
| 9 | MOCS | Condicionada | Maquinaria, trabajadores y vehículos | Apoyo parcial CR-05 | Requiere gestión/verificación de acceso |

---

## 3. Links de obtención en el orden propuesto

### 1. SH17

**Uso recomendado:** primer dataset a descargar para EPP general.

- Repositorio oficial: https://github.com/ahmadmughees/SH17dataset
- Kaggle: https://www.kaggle.com/datasets/mugheesahmad/sh17-dataset-for-ppe-detection

**Notas:**

- Contiene imágenes y anotaciones para detección de PPE.
- El repositorio indica que los datos pueden obtenerse desde Kaggle o mediante script de descarga desde fuentes originales.
- Registrar licencia, versión y fecha de descarga.

---

### 2. SHEL5K

**Uso recomendado:** refuerzo fuerte para CR-01, especialmente casco / no casco.

- Página de datos en Mendeley Data: https://data.mendeley.com/datasets/9rcv8mm682/4
- Repositorio asociado: https://github.com/MoyoG/SHEL5K

**Notas:**

- Dataset enfocado en seguridad por uso de casco.
- Útil para evaluar robustez de detección de casco y ausencia de casco.
- No aporta cobertura directa para chaleco.

---

### 3. CHV — Color Helmet and Vest

**Uso recomendado:** dataset clave por pertinencia visual al dominio construcción.

- Repositorio oficial: https://github.com/ZijianWang-ZW/PPE_detection
- Google Drive directo: https://drive.google.com/file/d/1fdGn67W0B7ShpBDbbQpUF0ScPQa4DR0a/view?usp=sharing
- Paper: https://www.mdpi.com/1424-8220/21/10/3478

**Notas:**

- Contiene persona, chaleco y cascos por color.
- Muy útil para CR-01 y CR-02.
- Verificar estructura original de anotaciones antes de convertir.

---

### 4. Construction-PPE

**Uso recomendado:** dataset muy práctico para evaluación por tener clases explícitas de EPP faltante.

- Documentación oficial Ultralytics: https://docs.ultralytics.com/datasets/detect/construction-ppe/
- YAML oficial: https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/construction-ppe.yaml
- Descarga directa ZIP: https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip

**Notas:**

- Incluye clases como `helmet`, `vest`, `Person`, `no_helmet`, etc.
- Viene con estructura `train/val/test`.
- Revisar licencia AGPL-3.0 y documentar implicancias para redistribución.

---

### 5. GDUT-HWD

**Uso recomendado:** refuerzo de CR-01 y análisis de casco por color.

- Repositorio oficial: https://github.com/wujixiu/helmet-detection
- Google Drive: https://drive.google.com/drive/folders/12WtXQyM-7jWvWPtCXZlnycsIK72ClHgu?usp=sharing
- Baidu Yun: https://pan.baidu.com/s/1_Jj56B05YpUv5iLB9JMb4g  
  Password: `dstk`

**Notas:**

- Dataset centrado en hardhat / color / ausencia.
- Útil para contrastar CR-01 contra datasets de casco más específicos.
- Verificar formato y conversión a COCO / YOLO.

---

### 6. SHWD — Safety Helmet Wearing Dataset

**Uso recomendado:** apoyo para casco vs cabeza/persona sin casco.

- Repositorio oficial: https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset
- Google Drive: https://drive.google.com/file/d/1qWm7rrwvjAWs1slymbrLaCf7Q-wnGLEX/view?usp=drive_open
- Baidu Drive: https://pan.baidu.com/s/1UbFkGm4EppdAU660Vu7SdQ

**Notas:**

- El repositorio indica formato Pascal VOC.
- Clases operativas principales: `hat` y `person` como negativo/no casco.
- Verificar si el split incluido sirve directamente o si conviene generar uno propio reproducible.

---

### 7. SODA — Site Object Detection dAtaset

**Uso recomendado:** contexto de obra, entidades auxiliares y preparación de extensiones CR-05 / CR-06.

- Página oficial del proyecto: https://linjiarui.net/en/portfolio/2022-02-22-SODA-site-object-detection-dataset-for-deep-learning-in-construction
- Link de acceso indicado por la página oficial: https://hkustconnect-my.sharepoint.com/:f:/g/personal/ycdeng_connect_ust_hk/EiQLht3OhstGnKXrjFXyRZYBIXFjUC43jUUNVBXfM_kkKg?e=jJ2Nhv
- Alternativa Roboflow Universe: https://universe.roboflow.com/sungkyunkwan-university-9qezx/sodaconstruction-awtup

**Notas:**

- Útil para contexto de construcción, persona, casco, chaleco, máquinas, layout y elementos como fence/scaffold.
- No resuelve por sí solo CR-05 o CR-06 como patrón completo.
- Debe separarse del corpus obligatorio CR-01/CR-02 para no mezclar alcance.

---

### 8. Pictor-PPE / Pictor-v3

**Uso recomendado:** dataset condicionado para cumplimiento casco/chaleco.

- Repositorio oficial: https://github.com/ciber-lab/pictor-ppe
- Google Drive: https://drive.google.com/drive/folders/1akhyTNVrkqMMcIFUQCEbW5ehfmG0CdYH?usp=sharing
- Paper: https://www.sciencedirect.com/science/article/pii/S0926580519306838

**Notas:**

- Contiene combinaciones de cumplimiento PPE: worker, hard hat, safety vest.
- Antes de usarlo en entrenamiento/evaluación, verificar:
  - licencia efectiva;
  - permisos de redistribución;
  - si la versión descargada coincide con la versión documentada;
  - formato real de anotaciones.

---

### 9. MOCS — Moving Objects in Construction Sites

**Uso recomendado:** extensión condicionada para maquinaria, vehículos y trabajadores.

- Página oficial indicada por OpenConstruction: https://www.anlab340.com/Archives/IndexArctype/index/t_id/17.html
- Referencia desde OpenConstruction: https://github.com/YUZ128pitt/OpenConstruction
- Paper/referencia: https://www.researchgate.net/publication/347870835_Dataset_and_benchmark_for_detecting_moving_objects_in_construction_sites

**Notas:**

- Dataset grande orientado a objetos móviles en construcción.
- Útil para CR-05, pero no trae directamente la condición “maquinaria cerca de peatones”.
- Puede requerir solicitud de acceso o verificación manual del portal oficial.

---

## 4. Benchmarks complementarios

Estos no son parte del corpus principal de EPP, pero conviene tenerlos registrados para tracking y evaluación OVD+MOT.

### MOT17

**Uso recomendado:** verificación de módulo de tracking, no validación de dominio construcción.

- Página oficial: https://motchallenge.net/data/MOT17/
- Descarga directa: https://motchallenge.net/data/MOT17.zip
- Devkit/evaluación: https://github.com/dendorferpatrick/MOTChallengeEvalKit

### OVT-B

**Uso recomendado:** benchmark para open-vocabulary multi-object tracking.

- Repositorio oficial: https://github.com/Coo1Sea/OVT-B-Dataset
- Google Drive: https://drive.google.com/drive/folders/1Qfmb6tEF92I2k84NgrkjEbOKnFlsrTVZ?usp=drive_link
- Baidu Yun: https://pan.baidu.com/s/1hy44z_om609jIhXjRxXCug?pwd=8yy3

---

## 5. Estructura local sugerida

```text
datasets/
  raw/
    sh17/
    shel5k/
    chv/
    construction_ppe/
    gdut_hwd/
    shwd/
    soda/
    pictor_ppe/
    mocs/
  processed/
    coco/
    yolo/
    odvg/
  splits/
    cr01_cr02/
      train.json
      val.json
      test.json
      split_manifest.csv
  registry/
    datasets_metadata.yaml
    class_mapping.yaml
    license_registry.md
    download_log.md
  scripts/
    download/
    convert/
    validate/
    split/
```

---

## 6. Registro mínimo por dataset

Completar un archivo `datasets/registry/datasets_metadata.yaml` con esta estructura:

```yaml
- id: sh17
  name: SH17
  source_url: "https://github.com/ahmadmughees/SH17dataset"
  download_url: "https://www.kaggle.com/datasets/mugheesahmad/sh17-dataset-for-ppe-detection"
  downloaded_at: "YYYY-MM-DD"
  original_format: "YOLO / Pascal VOC / verificar"
  target_formats:
    - coco
    - yolo
    - odvg
  license: "CC BY-NC-SA 4.0 / verificar contra fuente descargada"
  classes_original: []
  classes_mapped:
    person: []
    helmet: []
    vest: []
    no_helmet: []
    no_vest: []
  covered_conditions:
    - CR-01
    - CR-02
  split_policy: "official / custom_seeded"
  split_seed: 42
  notes: ""
```

---

## 7. Normalización de clases

### Clases canónicas iniciales

```yaml
canonical_classes:
  person:
    description: "Persona, trabajador o peatón visible."
  helmet:
    description: "Casco de seguridad visible."
  vest:
    description: "Chaleco reflectivo o de seguridad visible."
  no_helmet:
    description: "Persona/cabeza sin casco, cuando exista etiqueta explícita."
  no_vest:
    description: "Persona sin chaleco, cuando exista etiqueta explícita."
```

### Mapeo inicial esperado

| Dataset | Mapeo preliminar |
|---|---|
| SH17 | `person`, `helmet`, `safety-vest` → canónicas |
| SHEL5K | `helmet`, `person with helmet`, `person without helmet`, `head`, `face` |
| CHV | `person`, `vest`, `blue helmet`, `red helmet`, `white helmet`, `yellow helmet` |
| Construction-PPE | `helmet`, `vest`, `Person`, `no_helmet`, otros EPP |
| GDUT-HWD | `blue`, `white`, `yellow`, `red`, `none` |
| SHWD | `hat`, `person` |
| SODA | `Person`, `Helmet`, `Vest`, `Fence`, `Scaffold`, máquinas/materiales |
| Pictor-PPE | `worker`, `hat`, `vest`, combinaciones de cumplimiento |
| MOCS | `Worker`, máquinas y vehículos |

---

## 8. Política de partición recomendada

El documento metodológico no fija porcentajes definitivos. Para implementación, se recomienda:

1. **Respetar splits oficiales** cuando existan y sean compatibles.
2. Si no hay split confiable, generar split custom reproducible.
3. Congelar `test` antes de cualquier fine-tuning.
4. Evaluar baseline zero-shot sobre el mismo `test` que la variante ajustada.
5. Evitar solapamientos entre datasets combinados.
6. Registrar semilla, criterio y manifiesto de partición.

### Propuesta inicial defendible

```yaml
split_policy:
  seed: 42
  train: 0.70
  val: 0.15
  test: 0.15
  constraints:
    - "train, val y test estrictamente disjuntos"
    - "test congelado antes de entrenamiento"
    - "no aplicar data augmentation sobre val/test"
    - "deduplicación perceptual antes del split"
    - "mantener trazabilidad imagen -> dataset origen"
```

### Fine-tuning acotado

```yaml
fine_tuning_subset:
  min_images: 500
  max_images: 2000
  conditions:
    - CR-01
    - CR-02
  requirement:
    - "baseline zero-shot evaluada antes"
    - "test congelado"
    - "subset documentado por manifest"
```

---

## 9. Tareas concretas de implementación

### Semana 1 — Descarga y registro

- [ ] Crear estructura `datasets/`.
- [ ] Crear `download_log.md`.
- [ ] Descargar SH17.
- [ ] Descargar SHEL5K.
- [ ] Descargar CHV.
- [ ] Descargar Construction-PPE.
- [ ] Registrar fuente, licencia, tamaño, hash y fecha.
- [ ] Verificar que imágenes y anotaciones abren correctamente.

### Semana 2 — Conversión y validación

- [ ] Inspeccionar formatos originales.
- [ ] Convertir a COCO.
- [ ] Convertir a YOLO si corresponde.
- [ ] Preparar ODVG si se usa Grounding DINO.
- [ ] Validar bounding boxes fuera de rango.
- [ ] Detectar imágenes corruptas.
- [ ] Generar resumen por clase.

### Semana 3 — Mapeo de clases y splits

- [ ] Definir `class_mapping.yaml`.
- [ ] Normalizar clases a canónicas.
- [ ] Generar test congelado.
- [ ] Crear `split_manifest.csv`.
- [ ] Ejecutar deduplicación básica.
- [ ] Separar corpus obligatorio CR-01/CR-02 de datasets contextuales.

### Semana 4 — Baseline inicial

- [ ] Ejecutar baseline zero-shot con prompts primarios.
- [ ] Registrar métricas por dataset.
- [ ] Identificar falsos positivos/falsos negativos típicos.
- [ ] Seleccionar subset candidato de fine-tuning.
- [ ] Congelar versión `dataset-v0.1`.

---

## 10. Criterio de cierre de esta etapa

La etapa de obtención y preparación queda cerrada cuando existan:

- `datasets_metadata.yaml`
- `license_registry.md`
- `class_mapping.yaml`
- `split_manifest.csv`
- corpus convertido en COCO/YOLO/ODVG según necesidad;
- test set congelado para CR-01 y CR-02;
- log de descarga y verificación;
- reporte simple de distribución por clase/dataset;
- decisión documentada sobre qué datasets entran al baseline y cuáles quedan como extensión.
