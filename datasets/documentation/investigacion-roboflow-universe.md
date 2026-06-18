# Roboflow Universe — Datasets de Construcción / EPP

Investigación detallada de los datasets de detección de EPP (Equipo de Protección Personal) y seguridad en obra disponibles en **Roboflow Universe**, evaluados como candidatos para E-OVRT-VDP.

> **Fecha de investigación:** 2026-06-17
> **Fuentes:** búsqueda en https://universe.roboflow.com/search?q=construction%20safety y https://universe.roboflow.com/browse/construction/ppe
> **Objetivo:** identificar datasets que aporten ground-truth para **CR-01** (sin casco) y **CR-02** (sin chaleco), priorizando los que tienen **clases negativas explícitas** (`NO-Hardhat`, `NO-Safety-Vest`).

---

## 1. Por qué Roboflow Universe importa para este proyecto

La mayoría de los datasets clásicos de EPP (CHV, SHEL5K, SH17) anotan **presencia** de casco/chaleco, pero no **ausencia**. Para detectar CR-01/CR-02 con ground-truth real necesitamos datasets con clases negativas. Roboflow Universe destaca porque varios de sus datasets de "Construction Site Safety" incluyen exactamente esas clases:

- `NO-Hardhat` → ground-truth directo de CR-01
- `NO-Safety-Vest` → ground-truth directo de CR-02

Esto los hace **estructuralmente superiores** para evaluación de condiciones de riesgo, frente a datasets que solo marcan presencia.

### Consideración clave de licencia

Los datasets de Roboflow Universe se publican mayoritariamente bajo **CC BY 4.0** (atribución), apta para uso académico, publicación de métricas y redistribución con cita. Cada dataset muestra su licencia en la página de descarga; **siempre verificar al exportar**, ya que el autor puede haber elegido otra.

---

## 2. Dataset estrella: Construction Site Safety (Roboflow Universe Projects)

| Campo | Valor |
|---|---|
| **URL** | https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety |
| **Autor** | Roboflow Universe Projects (oficial) |
| **Imágenes** | 717 (dataset base) |
| **Versiones** | 30+ |
| **Modelos entrenados** | 7 |
| **mAP@50** | 84.1% |
| **Precision** | 92.7% |
| **Recall** | 77.4% |
| **Vistas (~8.33k usos)** | Es el referente del espacio en Universe |

### Clases (25)

```
truck, bus, Mask, vehicle, van, fire hydrant, SUV, Person, Excavator,
Hardhat, sedan, trailer, Ladder, Safety Vest, dump truck, Gloves,
machinery, mini-van, NO-Hardhat, NO-Mask, NO-Safety Vest, Safety Cone,
semi, truck and trailer, wheel loader
```

**Clases relevantes para E-OVRT-VDP** (resaltadas):
- ✅ `Person`
- ✅ `Hardhat` / `NO-Hardhat` ← **CR-01 directo**
- ✅ `Safety Vest` / `NO-Safety Vest` ← **CR-02 directo**
- ✅ `Gloves`, `Mask` / `NO-Mask` (condiciones futuras)
- ➕ `Excavator`, `machinery`, `vehicle`, `Ladder`, `Safety Cone` (CR-05/CR-06 futuro: maquinaria cerca de peatones)

### Split (versión 27, ejemplo con augmentation)
- Train: 2 605 imágenes (93%)
- Valid: 114 imágenes (4%)
- Test: 82 imágenes (3%)

> El conteo sube respecto a las 717 base por las augmentations aplicadas en esa versión. Para evaluación honesta conviene exportar una versión **sin augmentation** o las imágenes raw.

### Aplicaciones declaradas por el autor
1. **Compliance Monitoring** — verificar que los trabajadores usan EPP
2. **Accident Detection & Prevention** — detectar persona sin casco/chaleco cerca de maquinaria pesada en tiempo real
3. **Access Control** — permitir acceso solo a personal con EPP correcto
4. **Equipment & Vehicle Tracking**
5. **Job Site Documentation & Reporting**

> El caso de uso #2 es **textualmente CR-01/CR-02 + CR-05** del proyecto. Este dataset está conceptualmente alineado con E-OVRT-VDP.

### Relación con el corpus actual
⚠️ **Importante:** el dataset `construction-ppe.zip` de Ultralytics que ya descargamos (`datasets/raw/construction_ppe/`) es una **versión derivada/empaquetada de este mismo proyecto**, con distinto recorte de clases y formato YOLO. Funcionalmente ya tenemos cubierta su esencia. Vale la pena descargar una versión nueva de Universe solo si queremos:
- Las clases de maquinaria/vehículos (futuro CR-05/CR-06)
- Más imágenes con `NO-Safety Vest` explícito (que Construction-PPE de Ultralytics no trae)

---

## 3. Construction PPE (skcet)

| Campo | Valor |
|---|---|
| **URL** | https://universe.roboflow.com/skcet-g4h72/construction-ppe-rdhzo |
| **Autor** | skcet |
| **Imágenes** | 8 800 |
| **Versiones** | 3 |
| **Modelos** | 3 |
| **mAP@50** | 55.1% ⚠️ (bajo — indica anotaciones ruidosas/inconsistentes) |
| **Precision** | 57.4% |
| **Recall** | 68.7% |
| **Publicado** | 2024-03 (v3: 2023-12-20) |

### Clases (16)

```
Helmet, helmet, vest, hat, glasses, Human, Safety Vest, boots, gloves,
Gloves, no boot, no boots, no gloves, no hat, no vest, Safety Boot
```

**Análisis de calidad:**
- ⚠️ **Clases duplicadas con distinta capitalización**: `Helmet`/`helmet`, `gloves`/`Gloves`, `boots`/`no boot`/`no boots`. Requiere limpieza/normalización antes de usar.
- ✅ **Único del grupo con `no vest`** — relevante para la brecha de CR-02.
- ✅ También tiene `no hat` (≈ no_helmet), `no gloves`, `no boots`.

### Valoración para E-OVRT-VDP
- **Volumen:** 8.8k imágenes es el mayor del grupo — útil si se necesita masa para fine-tuning.
- **Riesgo:** mAP propio de 55% sugiere etiquetado inconsistente. Mapeo canónico requeriría unificar duplicados:
  ```yaml
  helmet: [Helmet, helmet, hat]
  vest: [vest, Safety Vest]
  no_helmet: [no hat]
  no_vest: [no vest]   # ← la clase que nos falta
  person: [Human]
  ```
- **Decisión:** candidato secundario, **solo si necesitamos `no_vest`** o volumen. Exige curación previa.

---

## 4. PPE Dataset for Workplace Safety (SiaBar)

| Campo | Valor |
|---|---|
| **URL** | https://universe.roboflow.com/siabar/ppe-dataset-for-workplace-safety |
| **Autor** | SiaBar (GitHub: BabakBar) |
| **Imágenes** | 1 600 |
| **Versiones** | 2 (v2: 2024-01-03) |
| **Modelos** | 1 |
| **mAP@50** | 97.8% ✅ (muy alto — anotaciones limpias) |
| **Precision** | 96.5% |
| **Recall** | 93.9% |

### Clases (8)

```
Helmet, Mask, Glass, Vest, Glove, Person, Boots, Ear-protection
```

**Análisis:**
- ✅ Excelente calidad de anotación (mAP 97.8%).
- ✅ Clases limpias, sin duplicados.
- ❌ **Sin clases negativas** (no_helmet, no_vest) → solo detecta presencia de EPP.
- Descripción oficial: enfocado a ambientes "industriales y de construcción"; las muestras se ven más industriales que de obra civil a cielo abierto.

### Valoración para E-OVRT-VDP
- ⭐ Baja prioridad para CR-01/CR-02 (no tiene negativos).
- Podría servir como refuerzo de **detección de presencia** de EPP de alta calidad, o para validar el "lado positivo" del clasificador.

---

## 5. Variantes alternativas de "Construction Site Safety"

Existen múltiples forks/re-anotaciones del dataset estrella. Documentados por contraste:

### 5.1 construction site safety (007)

| Campo | Valor |
|---|---|
| **URL** | https://universe.roboflow.com/007-kd2zw/construction-site-safety-rmep1 |
| **Imágenes** | 2 800 |
| **mAP@50** | 79.1% / P 88.4% / R 71.9% |
| **Clases (10)** | Mask, vehicle, Person, Hardhat, machinery, **No-Hardhat**, No-Mask, **No-Safety-Vest**, Safety-Cone, Safety-Vest |

✅ Vocabulario más acotado y centrado en EPP + negativos. **2 800 imgs con mAP 79%** lo hace un candidato interesante: más volumen que el dataset base (717) manteniendo `No-Hardhat`/`No-Safety-Vest`.

### 5.2 Construction Site Safety (Geniuspond)

| Campo | Valor |
|---|---|
| **URL** | https://universe.roboflow.com/geniuspond/construction-site-safety-5w9lj |
| **Imágenes** | 628 |
| **mAP@50** | 51.3% ⚠️ / P 72.3% / R 46.2% |
| **Clases (25)** | Mismas 25 del dataset estrella (truck, bus, Excavator, NO-Hardhat, NO-Safety-Vest, etc.) |

⚠️ Misma taxonomía que el oficial pero menor calidad (mAP 51%) y menos imágenes. No prioritario.

---

## 6. Otros datasets del catálogo PPE (contextuales)

De `browse/construction/ppe`, relevantes para condiciones futuras (no CR-01/CR-02):

| Dataset | Imágenes | Foco | Uso potencial |
|---|---|---|---|
| **Eye Protection** (Roboflow) | 6 300 | Gafas/goggles | Condición futura de protección ocular |
| **Underground pedestrian** | — | Peatones en túneles/minería | CR-05 (peatones cerca de maquinaria) |
| **fire extinguisher** (E. N. Coleman) | 242 | Extintores | Inventario de seguridad (fuera de alcance actual) |

---

## 7. Tabla comparativa global

| Dataset | Imgs | Clases | `NO-Hardhat` | `NO-Vest` | mAP@50 | Calidad | Prioridad CR-01/02 |
|---|---|---|---|---|---|---|---|
| **CSS — Roboflow Univ. Projects** ⭐ | 717 | 25 | ✅ | ✅ | 84.1% | Alta | ⭐⭐⭐ |
| **CSS — 007** | 2 800 | 10 | ✅ | ✅ | 79.1% | Alta | ⭐⭐⭐ |
| **Construction PPE — skcet** | 8 800 | 16 | ✅ (no hat) | ✅ (no vest) | 55.1% | Media-baja | ⭐⭐ (volumen / `no_vest`) |
| **CSS — Geniuspond** | 628 | 25 | ✅ | ✅ | 51.3% | Baja | ⭐ |
| **PPE Workplace — SiaBar** | 1 600 | 8 | ❌ | ❌ | 97.8% | Muy alta | ⭐ (solo presencia) |
| **Eye Protection** | 6 300 | — | — | — | — | — | Futuro (ocular) |

---

## 8. Recomendaciones

### Para CR-01 / CR-02 (corto plazo)
1. **CSS — 007 (2 800 imgs)** o el **CSS oficial (717)** son los mejores candidatos para *evaluación con ground-truth de ausencia de EPP*. Ambos tienen `NO-Hardhat` y `NO-Safety-Vest` explícitos.
2. Ya tenemos cubierta la esencia del CSS oficial vía Construction-PPE (Ultralytics). El valor incremental de Roboflow es:
   - `NO-Safety-Vest` explícito (nos falta `no_vest`)
   - Más volumen y diversidad de escenas

### Para llenar la brecha `no_vest`
- **skcet (8.8k)** es el único con `no vest`, pero requiere curación por clases duplicadas y mAP bajo.
- **CSS — 007** tiene `No-Safety-Vest` con mejor calidad (mAP 79%) → **preferible** a skcet para `no_vest`.

### Para condiciones futuras (CR-05/CR-06: maquinaria/peatones)
- **CSS oficial / Geniuspond** (25 clases con Excavator, machinery, vehicles)
- **Underground pedestrian**

### Lo que NO aporta Roboflow
- Imágenes de obra en **contexto latinoamericano** (la diversidad geográfica/cultural sigue siendo una brecha; ahí CHV y MOCS aportan algo distinto).

---

## 9. Cómo descargar (mecánica Roboflow)

### Formatos de exportación disponibles
Roboflow exporta el mismo dataset a múltiples formatos sin re-anotar:
`YOLO (v5/v7/v8/v9/v11/v12/v26)`, `COCO JSON`, `Pascal VOC XML`, `TFRecord`, `CreateML`, `multiclass CSV`, entre otros.

> Para E-OVRT-VDP conviene **COCO** o **YOLO**, que son los formatos que nuestro `convert_datasets.py` ya maneja para normalizar a la vista `canonical_cr01_cr02`.

### Descarga vía API (requiere API key gratuita)
```python
pip install roboflow
```
```python
from roboflow import Roboflow
rf = Roboflow(api_key="TU_API_KEY")
project = rf.workspace("roboflow-universe-projects").project("construction-site-safety")
dataset = project.version(27).download("coco")   # o "yolov8", "voc", etc.
```

### Inferencia hosteada (solo prueba, no para el pipeline propio)
```python
pip install inference-sdk
```
```python
from inference_sdk import InferenceHTTPClient
client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key="API_KEY")
result = client.run_workflow(...)
```

> ⚠️ La API hosteada de Roboflow es para prototipado. El plano de medios de E-OVRT-VDP usa sus propios adaptadores (GDINO/YOLOE) sobre detección open-vocabulary; de Roboflow solo nos interesan las **imágenes + anotaciones** para evaluación/fine-tuning.

### Integración con el corpus
Tras descargar (formato YOLO o COCO), ubicar en:
```
datasets/raw/<dataset_id>/
```
y agregar la entrada correspondiente en:
- `datasets/registry/datasets_metadata.yaml` (metadata, licencia, SHA256)
- `datasets/registry/class_mapping.yaml` (mapeo al vocabulario canónico)
- `datasets/registry/license_registry.md`

Luego correr `convert_datasets.py` para generar las vistas `original` y `canonical_cr01_cr02`.

---

## 10. Licencias — resumen para uso académico

| Dataset | Licencia típica | Uso interno | Publicar métricas | Redistribuir |
|---|---|---|---|---|
| CSS (Roboflow Univ. Projects) | CC BY 4.0 | ✅ | ✅ con cita | ✅ con cita |
| CSS (007) | CC BY 4.0 | ✅ | ✅ con cita | ✅ con cita |
| Construction PPE (skcet) | CC BY 4.0 | ✅ | ✅ con cita | ✅ con cita |
| PPE Workplace (SiaBar) | CC BY 4.0 | ✅ | ✅ con cita | ✅ con cita |
| CSS (Geniuspond) | CC BY 4.0 | ✅ | ✅ con cita | ✅ con cita |

> **CC BY 4.0**: permite uso académico y comercial, modificación y redistribución, con la única obligación de **atribuir la fuente**. Sin restricción NonCommercial ni ShareAlike. Es la licencia más permisiva del corpus E-OVRT-VDP (a diferencia de SH17 que es NC-SA, o Construction-PPE de Ultralytics que es AGPL-3.0).
>
> ⚠️ La licencia se elige por dataset y por versión: **verificar en la pantalla de descarga de Roboflow antes de exportar**. El BibTeX de cita está disponible en cada página (sección "If you use this dataset in a research paper...").

### BibTeX

```bibtex
@misc{construction-site-safety_dataset,
  title  = {Construction Site Safety Dataset},
  type   = {Open Source Dataset},
  author = {Roboflow Universe Projects},
  howpublished = {\url{https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety}},
  journal = {Roboflow Universe}, publisher = {Roboflow}, year = {2023}
}

@misc{construction-ppe-rdhzo_dataset,
  title  = {Construction PPE Dataset},
  type   = {Open Source Dataset},
  author = {skcet},
  howpublished = {\url{https://universe.roboflow.com/skcet-g4h72/construction-ppe-rdhzo}},
  journal = {Roboflow Universe}, publisher = {Roboflow}, year = {2024}
}

@misc{ppe-dataset-for-workplace-safety_dataset,
  title  = {PPE Dataset for Workplace Safety Dataset},
  type   = {Open Source Dataset},
  author = {SiaBar},
  howpublished = {\url{https://universe.roboflow.com/siabar/ppe-dataset-for-workplace-safety}},
  journal = {Roboflow Universe}, publisher = {Roboflow}, year = {2024}
}
```

---

*Documento generado el 2026-06-17 a partir de investigación directa en Roboflow Universe. Las métricas (mAP/P/R) son las reportadas por cada autor en su modelo entrenado y sirven como proxy de la calidad de anotación, no como rendimiento esperado en E-OVRT-VDP.*
