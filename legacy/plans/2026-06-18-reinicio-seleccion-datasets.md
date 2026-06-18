# Reinicio de selección de datasets (v2) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruir el repo `e-ovrt_datasets` desde la selección: relevar y elegir datasets con criterios explícitos, y producir tres salidas (TRAIN para fine-tuning, BENCH con GT a nivel persona, DEMO curada) sobre el vocabulario v2 (`person`/`helmet`/`vest`/`bare_head`), habilitando el experimento comparativo E1/E2/E3 de detección de ausencia.

**Architecture:** Proceso secuencial por fases — primero seleccionar (artefactos de scoring auditables), después procesar. La infraestructura de conversión/curación es **dataset-agnóstica y config-driven** (se extiende `convert_datasets.py` con una vista `canonical_v2`); cada dataset seleccionado se incorpora como entrada de configuración. El GT del BENCH se ancla en **anotaciones negativas explícitas** (no en asociación espacial) para evitar circularidad con E1. La lógica de E1/E3 y los prompts viven en `e-ovrt_media-plane`; aquí solo se produce el dato + el GT + el contrato de medición.

**Tech Stack:** Python 3 (scripts standalone, sin package), Pillow; pytest para la lógica pura nueva (única dependencia dev agregada); YAML/CSV/JSON para artefactos de registry. Formatos de salida: COCO (pivote), YOLO (YOLOE), ODVG (GDINO/MM-GDINO).

## Global Constraints

- **Sin commits durante la ejecución.** El usuario crea una rama nueva al final y commitea todo junto. Ningún task incluye `git add`/`git commit`.
- **No procesar antes de seleccionar.** Las fases 3+ (conversión/curación) no arrancan hasta cerrar la selección (Fase 1) y la verificación (Fase 2).
- **`bare_head` solo desde negativos explícitos.** Prohibido derivar `bare_head` por resta `head − helmet` o desde `head`/`face` genéricos (spec §3.1, D9).
- **GT del BENCH desde anotaciones explícitas**, nunca por asociación espacial (spec §5, D10).
- **Vocabulario v2 fijo:** clases de detección `person`, `helmet`, `vest`, `bare_head`; atributos persona-nivel (solo BENCH) `has_helmet`, `has_vest`. `no_vest`/`no_helmet` NO son clases (D6).
- **No borrar lo existente:** vistas/splits actuales se marcan DEPRECATED, se regeneran tras selección (D8).
- **Licencia obligatoria** para BENCH/DEMO: CC BY 4.0 o más permisiva (spec §7, D4).
- Defaults numéricos a confirmar antes de ejecutar Fase 1: IoU 0.5, ≥150+150 casos/condición, N=50 imágenes muestreadas / umbral >15 % defectos, auditoría ≥10 %/≥200 imágenes.
- Rutas relativas a la raíz del repo `e-ovrt_datasets/`. Scripts resuelven paths con `Path(__file__).resolve().parents[...]` siguiendo el patrón existente.

---

## File Structure

**Nuevos artefactos de registry/documentación:**
- `datasets/registry/annotation_contract_v2.yaml` — definiciones de clase + matriz fuente×clase (exhaustiva/parcial/ausente). (Fase 3)
- `datasets/registry/selection_scoring.csv` — una fila por candidato; criterios, puntaje, decisión, rol. (Fase 1)
- `datasets/registry/bench_gt_audit.md` — resultado de la auditoría manual del GT del BENCH. (Fase 4)
- `datasets/documentation/2026-06-18-protocolo-experimental-ausencia.md` — protocolo de medición (E1/E2/E3, métricas, IoU, set de prompts/sinónimos congelados). (Fase 6)
- `datasets/documentation/2026-06-18-metodologia-seleccion.md` — narrativa de la rúbrica + justificación. (Fase 1)

**Código nuevo:**
- `datasets/scripts/select/quality_sample.py` — muestreo de N imágenes + render de cajas para el checklist de calidad. (Fase 1)
- `datasets/scripts/bench/build_person_gt.py` — construye GT persona-nivel desde negativos explícitos. (Fase 4)
- `datasets/scripts/bench/geometry.py` — helpers de IoU/contención (lógica pura, testeada). (Fase 4)
- `datasets/scripts/curate/build_role_views.py` — genera vistas TRAIN/BENCH/DEMO; control de fuga y balance. (Fase 5)
- `datasets/scripts/curate/leakage_check.py` — verifica separación de escenas TRAIN↔BENCH. (Fase 5)
- `datasets/tests/` — pytest para lógica pura nueva (`test_geometry.py`, `test_contract.py`, `test_bare_head_guard.py`, `test_person_gt.py`).

**Código modificado:**
- `datasets/scripts/convert/convert_datasets.py` — agregar vista `canonical_v2`, campo `canonical_v2_map` y `negative_classes` en `DatasetConfig`, branch en `category_maps`/`transform_category`, y guard anti-`bare_head`-derivado.

**Marcado DEPRECATED (no borrado):**
- `datasets/processed/{coco,yolo,odvg}/{canonical_cr01_cr02,finetuning_cr01_cr02}/`
- `datasets/splits/cr01_cr02/`

---

## Fase 0 — Preparación y deprecación

### Task 0.1: Marcar lo existente como DEPRECATED

**Files:**
- Create: `datasets/processed/DEPRECATED.md`
- Create: `datasets/splits/DEPRECATED.md`

**Interfaces:**
- Produces: convención de deprecación que el resto del plan asume (nada se borra).

- [ ] **Step 1: Escribir el aviso de deprecación de processed**

Crear `datasets/processed/DEPRECATED.md` con:

```markdown
# DEPRECATED

Las vistas `canonical_cr01_cr02/` y `finetuning_cr01_cr02/` (COCO/YOLO/ODVG) y los
splits asociados quedan DEPRECATED a partir del reinicio v2 (ver
`datasets/documentation/2026-06-17-reinicio-seleccion-datasets-design.md`).

Se conservan como referencia hasta tener reemplazo v2 validado. No usar como entrada
de fine-tuning ni de evaluación. Vocabulario nuevo: person/helmet/vest/bare_head.
```

- [ ] **Step 2: Escribir el aviso de deprecación de splits**

Crear `datasets/splits/DEPRECATED.md` con el mismo aviso adaptado a `splits/cr01_cr02/`.

- [ ] **Step 3: Verificar**

Run: `ls datasets/processed/DEPRECATED.md datasets/splits/DEPRECATED.md`
Expected: ambos archivos existen.

---

### Task 0.2: Crear scaffold de carpetas y tests

**Files:**
- Create: `datasets/scripts/select/.gitkeep`, `datasets/scripts/bench/.gitkeep`
- Create: `datasets/tests/conftest.py`
- Create: `datasets/tests/README.md`

**Interfaces:**
- Produces: ubicación de pytest (`datasets/tests/`) que usan las fases 3–5.

- [ ] **Step 1: Crear carpetas**

```bash
mkdir -p datasets/scripts/select datasets/scripts/bench datasets/tests
touch datasets/scripts/select/.gitkeep datasets/scripts/bench/.gitkeep
```

- [ ] **Step 2: Escribir `datasets/tests/conftest.py`**

```python
"""Fixtures compartidas para los tests de la lógica v2."""
import sys
from pathlib import Path

# Permite importar los scripts standalone como módulos en los tests.
REPO_ROOT = Path(__file__).resolve().parents[1]  # datasets/
sys.path.insert(0, str(REPO_ROOT / "scripts"))
```

- [ ] **Step 3: Escribir `datasets/tests/README.md`**

```markdown
# Tests (v2)

Cubren la lógica pura nueva del reinicio v2. Requiere `pytest`.

    pip install pytest
    pytest datasets/tests -q
```

- [ ] **Step 4: Verificar que pytest descubre la carpeta**

Run: `pytest datasets/tests -q`
Expected: "no tests ran" (sin errores de colección).

---

## Fase 1 — Survey y selección (decisión humana, artefactos auditables)

> Esta fase es de investigación + decisión. No se procesa nada. Produce la selección
> reproducible. Confirmar los defaults numéricos del Global Constraints antes de empezar.

### Task 1.1: Herramienta de muestreo de calidad de anotación

**Files:**
- Create: `datasets/scripts/select/quality_sample.py`
- Test: `datasets/tests/test_quality_sample.py`

**Interfaces:**
- Produces: `sample_image_ids(image_ids: list[str], n: int, seed: int) -> list[str]` — selección determinista de N ids; usada por el checklist de calidad (spec §7, criterio obligatorio operable).

- [ ] **Step 1: Escribir el test de muestreo determinista**

```python
# datasets/tests/test_quality_sample.py
from select.quality_sample import sample_image_ids

def test_sample_is_deterministic_for_seed():
    ids = [f"img_{i}" for i in range(100)]
    a = sample_image_ids(ids, n=50, seed=42)
    b = sample_image_ids(ids, n=50, seed=42)
    assert a == b
    assert len(a) == 50

def test_sample_caps_at_population():
    ids = [f"img_{i}" for i in range(10)]
    assert len(sample_image_ids(ids, n=50, seed=42)) == 10
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest datasets/tests/test_quality_sample.py -q`
Expected: FAIL (módulo `select.quality_sample` inexistente).

- [ ] **Step 3: Implementar `quality_sample.py`**

```python
"""Muestrea N imágenes de un dataset y renderiza sus cajas para revisión de calidad.

Uso CLI:
    python datasets/scripts/select/quality_sample.py --images <dir> --n 50 --seed 42 --out <dir>

La revisión es manual: se completa el checklist de calidad (ver metodología de selección).
"""
import argparse
import random
from pathlib import Path


def sample_image_ids(image_ids: list[str], n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    ids = sorted(image_ids)
    if n >= len(ids):
        return ids
    return sorted(rng.sample(ids, n))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--images", required=True, type=Path)
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    exts = {".jpg", ".jpeg", ".png"}
    ids = [f.name for f in args.images.iterdir() if f.suffix.lower() in exts]
    chosen = sample_image_ids(ids, args.n, args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "sampled.txt").write_text("\n".join(chosen))
    print(f"Muestreadas {len(chosen)}/{len(ids)} imágenes -> {args.out/'sampled.txt'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest datasets/tests/test_quality_sample.py -q`
Expected: PASS (2 tests).

---

### Task 1.2: Relevamiento de candidatos (survey)

**Files:**
- Create: `datasets/registry/selection_scoring.csv`

**Interfaces:**
- Produces: `selection_scoring.csv` con esquema fijo de columnas que consume Task 1.3.

- [ ] **Step 1: Crear el CSV con encabezado y los candidatos ya conocidos**

Crear `datasets/registry/selection_scoring.csv` con exactamente estas columnas:

```csv
dataset_id,fuente,url,licencia,imgs,clases_clave,anota_person,negativos_explicitos,calidad_defectos_pct,dominio_obra_civil,split_oficial,gt_persona,puntaje,decision,rol
construction_site_safety,Roboflow Universe Projects,https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety,CC BY 4.0,,Hardhat;NO-Hardhat;Safety Vest;NO-Safety Vest;Person,si,si,,si,,si,,pendiente,
chv,GitHub ZijianWang-ZW,https://github.com/ZijianWang-ZW/PPE_detection,sin-SPDX,1330,person;vest;helmets,si,no,,parcial,si,no,,pendiente,
mocs,Roboflow Universe,https://universe.roboflow.com/mocs/mocs-bowib,CC BY 4.0,1471,Worker,si,no,,si,si,no,,pendiente,
construction_ppe_skcet,Roboflow Universe,https://universe.roboflow.com/skcet-g4h72/construction-ppe-rdhzo,CC BY 4.0,8800,helmet;vest;no vest;...,si,si,55,parcial,si,parcial,,pendiente,
ppe_siabar,Roboflow Universe,https://universe.roboflow.com/siabar/ppe-dataset-for-workplace-safety,CC BY 4.0,1600,Helmet;Vest;Person,si,no,,no,si,no,,pendiente,
```

- [ ] **Step 2: Relevar candidatos adicionales y completar filas**

Investigar en Roboflow Universe (`construction safety`, `construction ppe`), papers (SH17, SHEL5K, CHV) y Kaggle. Para cada candidato nuevo, agregar una fila con los campos descriptivos completos (`licencia`, `imgs`, `clases_clave`, `negativos_explicitos`, `gt_persona`).

Acceptance: ≥6 candidatos en el CSV; todo candidato con `negativos_explicitos=si` y licencia CC BY 4.0+ marcado como prioritario para BENCH.

- [ ] **Step 3: Verificar el CSV**

Run: `python -c "import csv; rows=list(csv.DictReader(open('datasets/registry/selection_scoring.csv'))); print(len(rows),'candidatos'); assert all('dataset_id' in r for r in rows)"`
Expected: imprime el número de candidatos (≥6), sin error.

---

### Task 1.3: Calidad de anotación + scoring + decisión de rol

**Files:**
- Modify: `datasets/registry/selection_scoring.csv` (completar `calidad_defectos_pct`, `puntaje`, `decision`, `rol`)
- Create: `datasets/documentation/2026-06-18-metodologia-seleccion.md`

**Interfaces:**
- Consumes: `sample_image_ids` (Task 1.1), `selection_scoring.csv` (Task 1.2).
- Produces: la selección final (qué datasets, qué rol) que consumen las fases 2–5.

- [ ] **Step 1: Aplicar el checklist de calidad a cada candidato descargable de forma preliminar**

Para cada candidato viable, obtener una muestra (Roboflow permite preview/descarga de versión pequeña) y correr:

```bash
python datasets/scripts/select/quality_sample.py --images <muestra> --n 50 --seed 42 --out /tmp/qa/<dataset_id>
```

Revisar manualmente las 50 contra el checklist: cajas ajustadas, sin faltantes, sin duplicados de clase (p. ej. `Helmet`/`helmet`), clases consistentes. Anotar `calidad_defectos_pct` = (imágenes con ≥1 defecto)/50 × 100.

- [ ] **Step 2: Aplicar criterios obligatorios y puntuar**

En `selection_scoring.csv`, para cada fila:
- `decision = descartado` si `calidad_defectos_pct > 15` **o** licencia no permisiva para el rol pretendido.
- `puntaje` = suma de deseables presentes (gt_persona, dominio_obra_civil, negativos_explicitos, volumen, split_oficial).
- `rol` ∈ {TRAIN, BENCH, DEMO, TRAIN+BENCH, descartado}. **BENCH exige** `negativos_explicitos=si` **y** `licencia` permisiva.

- [ ] **Step 3: Escribir la metodología**

Crear `datasets/documentation/2026-06-18-metodologia-seleccion.md` con: la rúbrica (copiada de spec §7), la tabla resultante (referencia al CSV), y un párrafo de justificación por cada `decision`/`rol`.

- [ ] **Step 4: Verificar que hay al menos un dataset por rol obligatorio**

Run:
```bash
python -c "
import csv
rows=[r for r in csv.DictReader(open('datasets/registry/selection_scoring.csv')) if r['decision']!='descartado']
roles=' '.join(r['rol'] for r in rows)
assert 'BENCH' in roles, 'falta dataset para BENCH'
assert 'TRAIN' in roles, 'falta dataset para TRAIN'
print('Seleccionados:', [(r['dataset_id'], r['rol']) for r in rows])
"
```
Expected: imprime la lista de seleccionados; falla si no hay BENCH o TRAIN.

> **Checkpoint humano:** revisar la selección antes de continuar a Fase 2.

---

## Fase 2 — Descarga y verificación de los seleccionados

### Task 2.1: Scripts de descarga de los datasets seleccionados

**Files:**
- Create: `datasets/scripts/download/download_<dataset_id>.sh` (uno por dataset seleccionado no presente)

**Interfaces:**
- Consumes: la selección de Task 1.3.
- Produces: `datasets/raw/<dataset_id>/` con imágenes + anotaciones.

- [ ] **Step 1: Escribir un script de descarga por dataset seleccionado**

Seguir el patrón de `datasets/scripts/download/download_chv.sh` (descarga a `datasets/raw/<id>/`, imprime SHA256). Para datasets de Roboflow Universe, usar el export con API key del usuario (no hardcodear la key; leerla de `$ROBOFLOW_API_KEY`).

Ejemplo de estructura mínima (`download_construction_site_safety.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail
DEST="$(dirname "$0")/../../raw/construction_site_safety"
mkdir -p "$DEST"
: "${ROBOFLOW_API_KEY:?Definí ROBOFLOW_API_KEY}"
# curl del export COCO/YOLO de la versión elegida -> $DEST
# (URL exacta de la versión seleccionada en Fase 1)
echo "SHA256:"; find "$DEST" -type f -name '*.zip' -exec sha256sum {} \;
```

- [ ] **Step 2: Ejecutar las descargas**

Run: `bash datasets/scripts/download/download_<dataset_id>.sh` (por cada uno).
Expected: `datasets/raw/<dataset_id>/` poblado; SHA256 impreso.

- [ ] **Step 3: Verificar presencia y conteo**

Run: `find datasets/raw/<dataset_id> -type f \( -name '*.jpg' -o -name '*.png' \) | wc -l`
Expected: número de imágenes coincide (±) con `imgs` del CSV.

---

### Task 2.2: Registrar provenance y licencias

**Files:**
- Modify: `datasets/registry/datasets_metadata.yaml`
- Modify: `datasets/registry/license_registry.md`
- Modify: `datasets/registry/download_log.md`

**Interfaces:**
- Produces: provenance v2 que consume el registry final (Fase 7).

- [ ] **Step 1: Agregar entrada por dataset seleccionado en `datasets_metadata.yaml`**

Seguir el esquema existente (nombre, fuente, url, licencia, imgs, sha256, split, clases). Una entrada por dataset seleccionado.

- [ ] **Step 2: Agregar licencia y log de descarga**

Agregar fila en `license_registry.md` (dataset → licencia → habilitación por uso) y en `download_log.md` (fecha, comando, sha256).

- [ ] **Step 3: Verificar YAML válido**

Run: `python -c "import yaml; yaml.safe_load(open('datasets/registry/datasets_metadata.yaml')); print('ok')"`
Expected: `ok`.

---

## Fase 3 — Vocabulario v2 + contrato de anotación

### Task 3.1: Contrato de anotación v2

**Files:**
- Create: `datasets/registry/annotation_contract_v2.yaml`
- Test: `datasets/tests/test_contract.py`

**Interfaces:**
- Produces: `load_contract(path) -> dict` y la matriz fuente×clase que consume `build_role_views.py` (Fase 5) para decidir exhaustividad.

- [ ] **Step 1: Escribir el test del contrato**

```python
# datasets/tests/test_contract.py
import yaml
from pathlib import Path

CONTRACT = Path("datasets/registry/annotation_contract_v2.yaml")

def test_contract_defines_all_v2_classes():
    data = yaml.safe_load(CONTRACT.read_text())
    assert set(data["classes"]) == {"person", "helmet", "vest", "bare_head"}

def test_every_selected_dataset_declares_exhaustiveness():
    data = yaml.safe_load(CONTRACT.read_text())
    for ds, m in data["sources"].items():
        for cls in data["classes"]:
            assert m.get(cls) in {"exhaustiva", "parcial", "ausente"}, (ds, cls)
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `pytest datasets/tests/test_contract.py -q`
Expected: FAIL (archivo inexistente).

- [ ] **Step 3: Escribir `annotation_contract_v2.yaml`**

```yaml
# Contrato de anotación v2 (spec §4). Una entrada por dataset seleccionado.
classes:
  person:    "Cuerpo completo visible de la persona/trabajador (incluye cabeza)."
  helmet:    "El casco propiamente dicho (la prenda), caja ceñida al casco."
  vest:      "El chaleco reflectivo/de seguridad (la prenda), caja ceñida al torso."
  bare_head: "Cabeza descubierta de persona SIN casco. Solo desde negativo explícito."

rules:
  - "helmet y bare_head son mutuamente excluyentes sobre la misma cabeza."
  - "Una clase no exhaustiva en una fuente NO se trata como negativo en esa fuente."
  - "bare_head jamás se deriva por resta head - helmet."

# matriz fuente x clase: exhaustiva | parcial | ausente
sources:
  construction_site_safety:
    person: exhaustiva
    helmet: exhaustiva
    vest: exhaustiva
    bare_head: exhaustiva   # desde NO-Hardhat explícito
  # ... una entrada por cada dataset seleccionado en Fase 1
```

Completar `sources` con TODOS los datasets seleccionados (sus valores reales de exhaustividad surgen de la revisión de Fase 1).

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `pytest datasets/tests/test_contract.py -q`
Expected: PASS.

---

### Task 3.2: Agregar la vista `canonical_v2` y `bare_head` a `convert_datasets.py`

**Files:**
- Modify: `datasets/scripts/convert/convert_datasets.py` (`DatasetConfig`, `category_maps`, `transform_category`)
- Test: `datasets/tests/test_bare_head_guard.py`

**Interfaces:**
- Consumes: `DatasetConfig` existente.
- Produces: vista `"canonical_v2"` con clases `["person","helmet","vest","bare_head"]`; campo `canonical_v2_map: dict[str,str] | None`; guard `assert_no_derived_bare_head(config)`.

- [ ] **Step 1: Escribir el test del guard anti-derivación**

```python
# datasets/tests/test_bare_head_guard.py
import pytest
from convert.convert_datasets import DatasetConfig, assert_no_derived_bare_head

def test_guard_rejects_head_to_bare_head():
    cfg = DatasetConfig(
        dataset_id="x", source_format="yolo", canonical_map={},
        canonical_v2_map={"head": "bare_head"},
    )
    with pytest.raises(ValueError):
        assert_no_derived_bare_head(cfg)

def test_guard_allows_explicit_negative():
    cfg = DatasetConfig(
        dataset_id="x", source_format="yolo", canonical_map={},
        canonical_v2_map={"NO-Hardhat": "bare_head"},
    )
    assert_no_derived_bare_head(cfg) is None
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `pytest datasets/tests/test_bare_head_guard.py -q`
Expected: FAIL (`canonical_v2_map`/`assert_no_derived_bare_head` no existen).

- [ ] **Step 3: Extender `DatasetConfig`**

En `datasets/scripts/convert/convert_datasets.py`, agregar campos al dataclass (junto a `canonical_map`):

```python
    canonical_v2_map: dict[str, str] | None = None
    # clases-origen que son negativos explícitos a nivel cabeza/persona (para bare_head y GT del BENCH)
    negative_classes: dict[str, str] | None = None  # ej: {"NO-Hardhat": "no_helmet", "NO-Safety Vest": "no_vest"}
```

- [ ] **Step 4: Agregar el guard**

Agregar la función (cerca de `category_maps`):

```python
_FORBIDDEN_BARE_HEAD_SOURCES = {"head", "face", "head_with_helmet"}

def assert_no_derived_bare_head(config: DatasetConfig) -> None:
    """bare_head solo desde negativos explícitos; nunca desde head/face (spec §3.1)."""
    v2 = config.canonical_v2_map or {}
    for src, dst in v2.items():
        if dst == "bare_head" and src.lower() in _FORBIDDEN_BARE_HEAD_SOURCES:
            raise ValueError(
                f"{config.dataset_id}: bare_head derivado de '{src}' está prohibido (D9)."
            )
```

- [ ] **Step 5: Extender `category_maps` y `transform_category` con la vista v2**

En `category_maps(config, view)` agregar:

```python
    elif view == "canonical_v2":
        names = ["person", "helmet", "vest", "bare_head"]
        return names, {n: i for i, n in enumerate(names)}
```

En `transform_category(config, category, view)` agregar, antes del `return`:

```python
    if view == "canonical_v2":
        return (config.canonical_v2_map or {}).get(category)
```

- [ ] **Step 6: Ejecutar y verificar que pasa**

Run: `pytest datasets/tests/test_bare_head_guard.py -q`
Expected: PASS.

---

### Task 3.3: Configurar y convertir cada dataset seleccionado a `canonical_v2`

**Files:**
- Modify: `datasets/scripts/convert/convert_datasets.py` (`configs()` — entradas por dataset seleccionado)

**Interfaces:**
- Consumes: `assert_no_derived_bare_head`, vista `canonical_v2`, contrato (Task 3.1).
- Produces: `datasets/processed/{coco,yolo,odvg}/canonical_v2/<dataset_id>/`.

- [ ] **Step 1: Agregar `canonical_v2_map` y `negative_classes` por dataset en `configs()`**

Para cada dataset seleccionado, completar el mapeo v2. Ejemplo (construction_site_safety):

```python
        "construction_site_safety": DatasetConfig(
            dataset_id="construction_site_safety",
            source_format="yolo",
            yolo_label_dir=RAW / "construction_site_safety" / "labels",
            canonical_map={...},   # vista original/cr01_cr02 si se mantiene
            canonical_v2_map={
                "Person": "person",
                "Hardhat": "helmet",
                "Safety Vest": "vest",
                "NO-Hardhat": "bare_head",
            },
            negative_classes={"NO-Hardhat": "no_helmet", "NO-Safety Vest": "no_vest"},
        ),
```

- [ ] **Step 2: Correr el guard sobre todas las configs**

Run:
```bash
python -c "
from convert.convert_datasets import configs, assert_no_derived_bare_head
import sys; sys.path.insert(0,'datasets/scripts')
for c in configs().values():
    assert_no_derived_bare_head(c)
print('guard ok para', list(configs()))
"
```
Expected: imprime `guard ok ...` sin excepción.

- [ ] **Step 3: Convertir a la vista v2**

Run: `python datasets/scripts/convert/convert_datasets.py --datasets <ids seleccionados> --views canonical_v2`
(si el CLI no soporta `--views`, agregar el flag siguiendo el patrón de `--datasets`).
Expected: genera `datasets/processed/{coco,yolo,odvg}/canonical_v2/<id>/`.

- [ ] **Step 4: Verificar conteos de clase**

Run:
```bash
python -c "
import json, glob
for f in glob.glob('datasets/processed/coco/canonical_v2/*/*'):
    if f.endswith('.json'):
        d=json.load(open(f)); cats={c['id']:c['name'] for c in d['categories']}
        print(f, {cats[a['category_id']] for a in d['annotations']})
" | head
```
Expected: las clases presentes ⊆ {person, helmet, vest, bare_head}.

---

## Fase 4 — Construcción y auditoría del GT del BENCH

### Task 4.1: Helpers de geometría (lógica pura)

**Files:**
- Create: `datasets/scripts/bench/geometry.py`
- Test: `datasets/tests/test_geometry.py`

**Interfaces:**
- Produces: `iou(a, b) -> float` y `head_region(person_xyxy) -> tuple` (tercio superior), usados por el matching de medición (spec §6.2).

- [ ] **Step 1: Escribir el test de geometría**

```python
# datasets/tests/test_geometry.py
from bench.geometry import iou, head_region

def test_iou_identical_is_one():
    assert iou([0,0,10,10],[0,0,10,10]) == 1.0

def test_iou_disjoint_is_zero():
    assert iou([0,0,10,10],[20,20,30,30]) == 0.0

def test_head_region_is_top_third():
    # persona 0..30 en Y -> cabeza 0..10
    x0,y0,x1,y1 = head_region([0,0,10,30])
    assert (y0, y1) == (0, 10)
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `pytest datasets/tests/test_geometry.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `geometry.py`**

```python
"""Geometría pura para matching detección<->GT (spec §6.2)."""

def iou(a: list[float], b: list[float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / (area_a + area_b - inter)

def head_region(person_xyxy: list[float]) -> tuple[float, float, float, float]:
    """Tercio superior de la caja persona (región de cabeza)."""
    x0, y0, x1, y1 = person_xyxy
    return (x0, y0, x1, y0 + (y1 - y0) / 3.0)
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `pytest datasets/tests/test_geometry.py -q`
Expected: PASS (3 tests).

---

### Task 4.2: Construcción del GT persona-nivel del BENCH

**Files:**
- Create: `datasets/scripts/bench/build_person_gt.py`
- Test: `datasets/tests/test_person_gt.py`

**Interfaces:**
- Consumes: anotaciones COCO `canonical_v2` del dataset BENCH + `negative_classes` de su config.
- Produces: `build_violation_records(annotations, negative_class_names) -> list[dict]` y un JSON `datasets/processed/bench_v2/<id>/person_gt.json` con registros `{bbox, condition, flag}` (`condition` ∈ {CR-01, CR-02}; `flag` = `no_helmet`/`no_vest`).

- [ ] **Step 1: Escribir el test de construcción de GT (anti-circularidad)**

```python
# datasets/tests/test_person_gt.py
from bench.build_person_gt import build_violation_records

def test_violations_come_only_from_explicit_negatives():
    anns = [
        {"category_name": "bare_head", "bbox_xyxy": [0,0,10,10], "source_class": "NO-Hardhat"},
        {"category_name": "helmet",    "bbox_xyxy": [5,5,15,15], "source_class": "Hardhat"},
        {"category_name": "vest",      "bbox_xyxy": [0,0,20,40], "source_class": "Safety Vest"},
    ]
    recs = build_violation_records(anns, negatives={"NO-Hardhat":"no_helmet"})
    # Solo el negativo explícito genera violación. NO se infiere desde ausencia de helmet.
    assert len(recs) == 1
    assert recs[0]["flag"] == "no_helmet"
    assert recs[0]["condition"] == "CR-01"
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `pytest datasets/tests/test_person_gt.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `build_person_gt.py`**

```python
"""GT persona-nivel del BENCH desde negativos explícitos (spec §5, anti-circularidad).

NO se infiere ausencia por geometría persona<->helmet: cada registro de violación
proviene de una anotación negativa explícita marcada por un humano.
"""
import argparse
import json
from pathlib import Path

_FLAG_TO_CONDITION = {"no_helmet": "CR-01", "no_vest": "CR-02"}


def build_violation_records(annotations: list[dict], negatives: dict[str, str]) -> list[dict]:
    records = []
    for ann in annotations:
        src = ann.get("source_class")
        flag = negatives.get(src)
        if flag is None:
            continue
        records.append({
            "bbox": ann["bbox_xyxy"],
            "flag": flag,
            "condition": _FLAG_TO_CONDITION[flag],
        })
    return records


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--coco", required=True, type=Path, help="COCO canonical_v2 del BENCH (con source_class)")
    p.add_argument("--negatives", required=True, help="JSON: {clase_origen: no_helmet|no_vest}")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    coco = json.loads(args.coco.read_text())
    negatives = json.loads(args.negatives)
    anns = coco["annotations"]  # deben incluir bbox_xyxy y source_class
    recs = build_violation_records(anns, negatives)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"violations": recs}, indent=2))
    print(f"{len(recs)} violaciones -> {args.out}")


if __name__ == "__main__":
    main()
```

> Nota: requiere que la conversión v2 preserve `source_class` por anotación en el COCO del
> BENCH. Si `write_coco` no lo emite, agregar el campo en Task 3.2/3.3 para el rol BENCH.

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `pytest datasets/tests/test_person_gt.py -q`
Expected: PASS.

- [ ] **Step 5: Generar el GT del dataset BENCH real**

Run: `python datasets/scripts/bench/build_person_gt.py --coco <coco bench> --negatives '{"NO-Hardhat":"no_helmet","NO-Safety Vest":"no_vest"}' --out datasets/processed/bench_v2/<id>/person_gt.json`
Expected: imprime el conteo de violaciones por condición.

---

### Task 4.3: Auditoría manual del GT del BENCH y poder estadístico

**Files:**
- Create: `datasets/registry/bench_gt_audit.md`

**Interfaces:**
- Consumes: `person_gt.json` (Task 4.2), `sample_image_ids` (Task 1.1).
- Produces: validación documentada del BENCH; gate para congelarlo.

- [ ] **Step 1: Muestrear y revisar**

Muestrear ≥10 % de las imágenes del BENCH (o ≥200, lo que sea menor) con `quality_sample.py` y verificar manualmente que cada `no_helmet`/`no_vest` del GT es correcto.

- [ ] **Step 2: Verificar poder estadístico**

Run:
```bash
python -c "
import json
v=json.load(open('datasets/processed/bench_v2/<id>/person_gt.json'))['violations']
from collections import Counter
c=Counter(r['condition'] for r in v); print(c)
assert c.get('CR-01',0) >= 150, 'CR-01 insuficiente'
"
```
Expected: imprime conteos; alerta si una condición no llega al mínimo (default 150). Documentar la limitación si CR-02 no alcanza.

- [ ] **Step 3: Escribir el reporte de auditoría**

Crear `datasets/registry/bench_gt_audit.md` con: tamaño de muestra, tasa de error encontrada, conteos por condición, y veredicto (BENCH congelado sí/no).

> **Checkpoint humano:** congelar el BENCH solo si la auditoría pasa.

---

## Fase 5 — Curación, splits, control de fuga y balance

### Task 5.1: Chequeo de fuga TRAIN↔BENCH

**Files:**
- Create: `datasets/scripts/curate/leakage_check.py`
- Test: `datasets/tests/test_leakage.py`

**Interfaces:**
- Produces: `find_leaks(train_ids, bench_ids) -> set[str]` (imágenes/escenas compartidas) que consume `build_role_views.py`.

- [ ] **Step 1: Escribir el test**

```python
# datasets/tests/test_leakage.py
from curate.leakage_check import find_leaks

def test_detects_shared_ids():
    assert find_leaks({"a","b","c"}, {"c","d"}) == {"c"}

def test_no_leak_when_disjoint():
    assert find_leaks({"a","b"}, {"c","d"}) == set()
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `pytest datasets/tests/test_leakage.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `leakage_check.py`**

```python
"""Verifica que TRAIN y BENCH no compartan imágenes/escenas (spec §8.5, G5)."""
import argparse
from pathlib import Path


def find_leaks(train_ids: set[str], bench_ids: set[str]) -> set[str]:
    return train_ids & bench_ids


def _ids(d: Path) -> set[str]:
    exts = {".jpg", ".jpeg", ".png"}
    return {f.stem for f in d.rglob("*") if f.suffix.lower() in exts}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--train", required=True, type=Path)
    p.add_argument("--bench", required=True, type=Path)
    args = p.parse_args()
    leaks = find_leaks(_ids(args.train), _ids(args.bench))
    if leaks:
        raise SystemExit(f"FUGA: {len(leaks)} ids compartidos: {sorted(leaks)[:10]}")
    print("Sin fuga TRAIN<->BENCH")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `pytest datasets/tests/test_leakage.py -q`
Expected: PASS.

---

### Task 5.2: Generar vistas por rol (TRAIN/BENCH/DEMO) con balance

**Files:**
- Create: `datasets/scripts/curate/build_role_views.py`
- Create: `datasets/splits/v2/<rol>_manifest.csv`
- Test: `datasets/tests/test_balance.py`

**Interfaces:**
- Consumes: `canonical_v2` (Task 3.3), `find_leaks` (Task 5.1), contrato (Task 3.1).
- Produces: `datasets/processed/{coco,yolo,odvg}/{train_v2,bench_v2,demo_v2}/` + manifests; `class_counts(manifest) -> dict[str,int]`.

- [ ] **Step 1: Escribir el test de balance**

```python
# datasets/tests/test_balance.py
from curate.build_role_views import meets_min_per_class

def test_balance_pass():
    assert meets_min_per_class({"person":500,"helmet":400,"vest":200,"bare_head":300}, minimum=150)

def test_balance_fail_on_vest():
    assert not meets_min_per_class({"person":500,"helmet":400,"vest":50,"bare_head":300}, minimum=150)
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `pytest datasets/tests/test_balance.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `build_role_views.py`**

```python
"""Arma las vistas por rol desde canonical_v2, respetando contrato, fuga y balance.

- TRAIN: une fuentes asignadas a TRAIN; excluye clases NO exhaustivas (contrato).
- BENCH: held-out; no comparte ids con TRAIN (leakage_check).
- DEMO: subconjunto chico de obra civil de alta calidad.
"""
import argparse
import json
from pathlib import Path


def meets_min_per_class(counts: dict[str, int], minimum: int) -> bool:
    return all(counts.get(c, 0) >= minimum for c in ("person", "helmet", "vest", "bare_head"))


# (resto del CLI: lee selection_scoring.csv para roles, copia/filtra anotaciones
#  canonical_v2 por rol, escribe manifests en datasets/splits/v2/, e invoca find_leaks)
```

Completar el CLI siguiendo el patrón de `generate_finetuning_cr01_cr02.py` (lectura de COCO, escritura de manifest CSV, resumen JSON), filtrando por el `rol` del CSV y por exhaustividad del contrato.

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `pytest datasets/tests/test_balance.py -q`
Expected: PASS.

- [ ] **Step 5: Generar las vistas y verificar fuga + balance**

Run:
```bash
python datasets/scripts/curate/build_role_views.py --scoring datasets/registry/selection_scoring.csv
python datasets/scripts/curate/leakage_check.py --train datasets/processed/coco/train_v2 --bench datasets/processed/coco/bench_v2
```
Expected: "Sin fuga TRAIN<->BENCH"; el resumen JSON reporta los conteos por clase y que TRAIN cumple el mínimo (o lista la estrategia de balanceo aplicada).

---

## Fase 6 — Protocolo experimental (contrato de medición)

### Task 6.1: Documentar el protocolo de medición

**Files:**
- Create: `datasets/documentation/2026-06-18-protocolo-experimental-ausencia.md`

**Interfaces:**
- Consumes: spec §6.
- Produces: el contrato de medición que `e-ovrt_media-plane` debe respetar (métricas, IoU, regla detección→persona, prompts/sinónimos congelados).

- [ ] **Step 1: Escribir el protocolo**

Documentar, copiando y expandiendo spec §6: métrica (P/R/F1 persona-nivel + mAP@50 secundario), IoU=0.5, la regla detección→persona por enfoque (E1/E2/E3, usando `geometry.head_region`), el **set de prompts congelado** por condición/enfoque, y el **mapeo de sinónimos** zero-shot. Marcar los defaults numéricos como confirmados.

- [ ] **Step 2: Verificar cobertura de la matriz**

Revisar que el documento cubra las 6 celdas medibles de la matriz §2.2 (E1/E2/E3 × sin-FT/con-FT) y, para cada una, cómo se obtiene el número.

Acceptance: cada celda de la matriz tiene método de cálculo explícito; los prompts están listados textualmente (no "TBD").

---

### Task 6.2: Congelar prompts y sinónimos en `e-ovrt_media-plane`

**Files:**
- Create (repo vecino): `e-ovrt_media-plane/configs/prompts/cr01_cr02_v2.yaml`

**Interfaces:**
- Consumes: el set de prompts del protocolo (Task 6.1).
- Produces: configs de prompts versionados que ejecuta el pipeline (fuera del alcance de medición de este repo).

- [ ] **Step 1: Crear el config de prompts**

Siguiendo `e-ovrt_media-plane/configs/prompts/` existente, crear `cr01_cr02_v2.yaml` con los prompts E3 (negación) y el mapeo de sinónimos zero-shot, idénticos a los del protocolo (Task 6.1).

- [ ] **Step 2: Verificar consistencia con el protocolo**

Run: `python -c "import yaml; p=yaml.safe_load(open('e-ovrt_media-plane/configs/prompts/cr01_cr02_v2.yaml')); print(list(p))"`
Expected: imprime las claves; los prompts coinciden textualmente con el protocolo.

> Cross-repo: este task toca el repo vecino. Coordinar con su `CLAUDE.md`.

---

## Fase 7 — Registry final y documentación

### Task 7.1: Actualizar el registry a v2

**Files:**
- Modify: `datasets/registry/class_mapping.yaml`
- Modify: `datasets/registry/conversion_report.md`

**Interfaces:**
- Consumes: todos los artefactos previos.
- Produces: registry coherente con v2.

- [ ] **Step 1: Reescribir `class_mapping.yaml` al vocabulario v2**

Reemplazar el mapeo CR-01/CR-02 por el v2 (person/helmet/vest/bare_head + atributos has_helmet/has_vest del BENCH), referenciando el contrato.

- [ ] **Step 2: Regenerar `conversion_report.md`**

Documentar conteos por dataset/rol/clase de las vistas v2 generadas (TRAIN/BENCH/DEMO).

- [ ] **Step 3: Verificar consistencia de clases**

Run:
```bash
python -c "
import yaml
cm=yaml.safe_load(open('datasets/registry/class_mapping.yaml'))
assert set(cm.get('detection_classes',[]))=={'person','helmet','vest','bare_head'}
print('class_mapping v2 ok')
"
```
Expected: `class_mapping v2 ok`.

---

### Task 7.2: Actualizar el índice de documentación y CLAUDE.md

**Files:**
- Modify: `datasets/documentation/README.md`
- Modify: `CLAUDE.md` (raíz del workspace) — sección de vocabulario/vistas

**Interfaces:**
- Produces: documentación de entrada apuntando a los artefactos v2.

- [ ] **Step 1: Actualizar `datasets/documentation/README.md`**

Agregar enlaces al diseño v2, metodología de selección, protocolo experimental y auditoría.

- [ ] **Step 2: Actualizar `CLAUDE.md`**

Actualizar la descripción del vocabulario canónico (de `no_helmet/no_vest` a `person/helmet/vest/bare_head` + atributos BENCH) y las vistas (`canonical_v2`, `train_v2`/`bench_v2`/`demo_v2`); marcar las vistas CR-01/CR-02 como DEPRECATED.

- [ ] **Step 3: Verificar enlaces**

Run: `grep -l "canonical_v2" CLAUDE.md datasets/documentation/README.md`
Expected: ambos archivos referencian `canonical_v2`.

---

## Self-Review (cobertura spec → plan)

| Spec | Task(s) |
|---|---|
| §1 entregables TRAIN/BENCH/DEMO | 5.2 |
| §2 E1/E2/E3 + matriz | 6.1 |
| §3.1 procedencia bare_head (D9) | 3.2 (guard), 3.3 |
| §4 contrato de anotación (D11) | 3.1 |
| §5 GT BENCH anti-circularidad (D10) | 4.1, 4.2, 4.3 |
| §6 protocolo de medición (D12) | 6.1, 6.2 |
| §6.5 / §7.1 balance y poder (D14) | 4.3, 5.2 |
| §7 rúbrica operable + scoring (D15) | 1.1, 1.2, 1.3 |
| §8.1 export por modelo (D16) | 3.3 (COCO/YOLO/ODVG) |
| §8.5 fuga / held-out (D13) | 5.1, 5.2 |
| §9 deprecación (D8) | 0.1 |
| §9 privacidad DEMO (D17) | 5.2 (filtro DEMO) + nota |
| registry v2 | 2.2, 7.1, 7.2 |

> Nota de placeholders permitidos: las fases 1–2 dependen de decisiones humanas y descargas
> externas; sus "valores reales" (qué datasets, conteos) se completan al ejecutar, pero el
> **procedimiento, artefactos y criterios de aceptación** están todos especificados.
