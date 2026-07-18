# Video-GT-Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el laboratorio de GT de video del spec
`docs/superpowers/specs/2026-07-11-video-gt-lab-design.md`: pipeline
prepare → preannotate (GDINO-base + ByteTrack) → corrección CVAT →
derivación determinística de `clip_gt.v2` → validación + doble anotación.

**Architecture:** Dos repos. En `e-ovrt_datasets` (stdlib + PyYAML): parser de
CVAT XML, derivación de episodios, validador, comparador kappa, prepare
(bash+ffmpeg). En `e-ovrt_media-plane` (entorno GPU): lógica pura de
asociación/suavizado/adelgazamiento/escritura XML + CLI de pre-anotación.
Cada etapa deja un artefacto en disco.

**Tech Stack:** Python 3.11, `xml.etree` (stdlib), PyYAML, pytest;
media-plane: transformers (GDINO-base), `supervision` (ByteTrack), OpenCV,
ffmpeg/ffprobe (sistema).

## Global Constraints

- **NUNCA commitear**: regla del workspace (`projects/CLAUDE.md`) — los pasos de
  checkpoint corren la suite completa y avisan; el commit lo pide el usuario.
- Repo datasets: scripts standalone, sin package; deps permitidas: stdlib,
  Pillow, **PyYAML** (nueva, documentada). Tests con fixtures sintéticos, sin
  media real. Imports en tests vía `pythonpath = datasets/scripts`
  (`from videogt.x import ...`).
- Repo media-plane: Python ≥3.11, ruff line-length 100, docstrings en español
  (estilo del repo). Dep nueva: `supervision` en extra `dev`.
- Conversión frame→ms: `round(frame * 1000 / fps)` — única fórmula, en un solo lugar.
- Pattern set default (parámetro, nunca hardcodeado en la lógica):
  `CR-01: 3000 ms`, `CR-02: 5000 ms`. Tolerancia de bordes declarada: `500 ms`.
- Condiciones: `CR-01` ← `has_helmet`, `CR-02` ← `has_vest`
  (atributo `False` = violación; ausencia de atributo = `None`, no evaluable).
- Formato de intercambio: **CVAT for video 1.1** sin extensiones.
- `clip_gt.v2`: schema del spec 43 §4 — este plan no lo modifica.

## File Structure

```
e-ovrt_datasets/
├── datasets/scripts/videogt/cvat_xml.py            # Task 1 — parser CVAT XML
├── datasets/scripts/videogt/derive_clip_gt.py      # Tasks 2-4 — derivación + CLI
├── datasets/scripts/bench/validate_clip_gt.py      # Task 5 — validador (spec 43 §5)
├── datasets/scripts/videogt/compare_annotations.py # Task 6 — kappa doble anotación
├── datasets/scripts/videogt/prepare_clip.sh        # Task 7 — etapa 0 (ffmpeg)
├── datasets/scripts/videogt/cvat_labels.json       # Task 7 — config labels CVAT
├── datasets-videos/{README.md,.gitignore}          # Task 7 — laboratorio
└── datasets/tests/test_{cvat_xml,derive_clip_gt,validate_clip_gt,compare_annotations}.py

e-ovrt_media-plane/
├── src/eovrt_media/tools/videogt.py                # Tasks 8-9 — lógica pura + writer XML
├── src/eovrt_media/tools/preannotate_video.py      # Task 10 — CLI pre-anotación
├── tests/tools/test_videogt.py                     # Tasks 8-10
└── pyproject.toml                                  # Task 10 — + supervision (dev)
```

---

### Task 1: Parser CVAT for video 1.1 (`cvat_xml.py`)

**Files:**
- Create: `datasets/scripts/videogt/cvat_xml.py`
- Test: `datasets/tests/test_cvat_xml.py`

**Interfaces:**
- Produces: `parse_cvat_video_xml(path) -> dict` con
  `{"tracks": [{"track_id": int, "label": str, "boxes": [{"frame": int,
  "outside": bool, "occluded": bool, "keyframe": bool,
  "attributes": {str: bool}}]}], "stop_frame": int | None}` (boxes ordenadas
  por frame); `attribute_states(track: dict, attr: str, end_frame: int) ->
  list[bool | None]` — timeline por frame `[0..end_frame]` con semántica
  escalón: `None` = no visible (antes de aparecer, `outside=1`, o atributo
  ausente), `bool` = valor vigente (fill-forward). Tasks 2-4 consumen ambas.

- [ ] **Step 1: Escribir tests que fallan**

```python
# datasets/tests/test_cvat_xml.py
"""Tests del parser CVAT for video 1.1 (fixture sintético, sin media)."""
import textwrap

from videogt.cvat_xml import attribute_states, parse_cvat_video_xml

CVAT_XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><size>10</size></task></meta>
      <track id="0" label="person" source="semi-auto">
        <box frame="2" keyframe="1" outside="0" occluded="0"
             xtl="10" ytl="10" xbr="50" ybr="90">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="5" keyframe="1" outside="0" occluded="1"
             xtl="12" ytl="10" xbr="52" ybr="90">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="8" keyframe="1" outside="1" occluded="0"
             xtl="12" ytl="10" xbr="52" ybr="90">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
      </track>
    </annotations>
""")


def _write(tmp_path, content):
    p = tmp_path / "annotations.xml"
    p.write_text(content)
    return p


def test_parse_tracks_y_stop_frame(tmp_path):
    doc = parse_cvat_video_xml(_write(tmp_path, CVAT_XML))
    assert doc["stop_frame"] == 9
    (track,) = doc["tracks"]
    assert track["track_id"] == 0 and track["label"] == "person"
    assert [b["frame"] for b in track["boxes"]] == [2, 5, 8]
    assert track["boxes"][0]["attributes"] == {"has_helmet": True, "has_vest": True}
    assert track["boxes"][2]["outside"] is True
    assert track["boxes"][1]["occluded"] is True


def test_attribute_states_escalon_y_outside(tmp_path):
    doc = parse_cvat_video_xml(_write(tmp_path, CVAT_XML))
    states = attribute_states(doc["tracks"][0], "has_helmet", end_frame=9)
    # frames 0-1: aun no aparece; 2-4: true; 5-7: false; 8-9: outside
    assert states == [None, None, True, True, True, False, False, False, None, None]


def test_atributo_ausente_es_none(tmp_path):
    xml = CVAT_XML.replace('<attribute name="has_vest">true</attribute>', "")
    doc = parse_cvat_video_xml(_write(tmp_path, xml))
    states = attribute_states(doc["tracks"][0], "has_vest", end_frame=4)
    assert states[3] is None  # atributo faltante NO fabrica violación
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd /home/simonll4/projects/e-ovrt_datasets && python3 -m pytest datasets/tests/test_cvat_xml.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'videogt'`

- [ ] **Step 3: Implementación mínima**

```python
# datasets/scripts/videogt/cvat_xml.py
"""Parser del formato 'CVAT for video 1.1' (stdlib xml.etree).

Extrae SOLO lo que la derivación de GT necesita: tracks con visibilidad
(``outside``) y atributos mutables por frame. Los atributos mutables de CVAT
son función escalón: mantienen su valor hasta el próximo keyframe que los
cambie — ``attribute_states`` materializa esa semántica frame a frame.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

_BOOL = {"true": True, "false": False}


def parse_cvat_video_xml(path: str | Path) -> dict:
    """Parsea un annotations.xml → {'tracks': [...], 'stop_frame': int | None}."""
    root = ET.parse(str(path)).getroot()
    stop_frame = None
    size_el = root.find("./meta/task/size")
    if size_el is not None and (size_el.text or "").strip().isdigit():
        stop_frame = int(size_el.text.strip()) - 1

    tracks = []
    for tr in root.findall("track"):
        boxes = []
        for b in tr.findall("box"):
            attributes = {}
            for a in b.findall("attribute"):
                raw = (a.text or "").strip().lower()
                if raw in _BOOL:
                    attributes[a.get("name")] = _BOOL[raw]
            boxes.append({
                "frame": int(b.get("frame")),
                "outside": b.get("outside") == "1",
                "occluded": b.get("occluded") == "1",
                "keyframe": b.get("keyframe") == "1",
                "attributes": attributes,
            })
        boxes.sort(key=lambda x: x["frame"])
        tracks.append({
            "track_id": int(tr.get("id")),
            "label": tr.get("label"),
            "boxes": boxes,
        })
    return {"tracks": tracks, "stop_frame": stop_frame}


def attribute_states(track: dict, attr: str, end_frame: int) -> list:
    """Timeline por frame [0..end_frame] del atributo, con semántica escalón.

    None = persona no visible (antes de aparecer o con outside=1) o atributo
    ausente en el keyframe vigente (no evaluable — nunca fabricar violación).
    Las oclusiones (occluded=1) NO interrumpen: la caja sigue viva.
    El track vale hasta end_frame salvo cierre explícito con outside=1
    (convención CVAT).
    """
    states: list = [None] * (end_frame + 1)
    boxes = track["boxes"]
    if not boxes:
        return states
    idx = 0
    current = None
    for f in range(end_frame + 1):
        while idx < len(boxes) and boxes[idx]["frame"] <= f:
            current = boxes[idx]
            idx += 1
        if current is None or current["outside"]:
            states[f] = None
        else:
            states[f] = current["attributes"].get(attr)
    return states
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python3 -m pytest datasets/tests/test_cvat_xml.py -q`
Expected: `3 passed`

- [ ] **Step 5: Checkpoint (sin commit — regla del workspace)**

Run: `python3 -m pytest datasets/tests/ -q` → toda la suite en verde.

---

### Task 2: Derivación — intervalos de violación por track

**Files:**
- Create: `datasets/scripts/videogt/derive_clip_gt.py`
- Test: `datasets/tests/test_derive_clip_gt.py`

**Interfaces:**
- Consumes: `attribute_states` (Task 1).
- Produces: `frame_to_ms(frame: int, fps: float) -> int`;
  `CONDITIONS = {"CR-01": "has_helmet", "CR-02": "has_vest"}`;
  `violation_intervals(states: list[bool | None], fps: float) -> list[dict]`
  con `{"start_ms": int, "end_ms": int}` (corridas contiguas de `False`;
  `True` y `None` cortan; `end_ms` = tiempo del primer frame posterior a la
  corrida); `track_condition_intervals(track: dict, end_frame: int,
  fps: float) -> list[dict]` con `{"condition_id", "track_id", "start_ms",
  "end_ms"}`. Task 3 consume esto.

- [ ] **Step 1: Tests que fallan**

```python
# datasets/tests/test_derive_clip_gt.py
"""Derivación de episodios desde timelines de atributos (spec §3.3)."""
from videogt.derive_clip_gt import (
    frame_to_ms,
    track_condition_intervals,
    violation_intervals,
)


def test_frame_to_ms_redondea():
    assert frame_to_ms(0, 30) == 0
    assert frame_to_ms(30, 30) == 1000
    assert frame_to_ms(1, 30) == 33


def test_violation_intervals_corta_por_none_y_true():
    # F=viola, T=cumple, N=no visible
    states = [True, False, False, None, False, False, True, False]
    got = violation_intervals(states, fps=10)
    assert got == [
        {"start_ms": 100, "end_ms": 300},   # frames 1-2, corta el None
        {"start_ms": 400, "end_ms": 600},   # frames 4-5, corta el True
        {"start_ms": 700, "end_ms": 800},   # frame 7, corre hasta el final
    ]


def test_violation_intervals_sin_violaciones():
    assert violation_intervals([True, True, None], fps=10) == []


def test_track_condition_intervals_mapea_condiciones():
    track = {
        "track_id": 3,
        "label": "person",
        "boxes": [
            {"frame": 0, "outside": False, "occluded": False, "keyframe": True,
             "attributes": {"has_helmet": False, "has_vest": True}},
            {"frame": 2, "outside": False, "occluded": False, "keyframe": True,
             "attributes": {"has_helmet": True, "has_vest": True}},
        ],
    }
    got = track_condition_intervals(track, end_frame=3, fps=10)
    assert got == [
        {"condition_id": "CR-01", "track_id": 3, "start_ms": 0, "end_ms": 200},
    ]
```

- [ ] **Step 2: Verificar fallo**

Run: `python3 -m pytest datasets/tests/test_derive_clip_gt.py -q`
Expected: FAIL — `No module named 'videogt.derive_clip_gt'`

- [ ] **Step 3: Implementación**

```python
# datasets/scripts/videogt/derive_clip_gt.py
"""Derivación determinística de clip_gt.v2 desde CVAT XML corregido.

Regla de oro (spec 43 §3.3): el GT sale del video corregido por el humano;
este script solo hace la aritmética. Las reglas viven en el spec del
laboratorio (docs/superpowers/specs/2026-07-11-video-gt-lab-design.md §3.3).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from videogt.cvat_xml import attribute_states  # noqa: E402

CONDITIONS = {"CR-01": "has_helmet", "CR-02": "has_vest"}
DEFAULT_PATTERN_SET_MS = {"CR-01": 3000, "CR-02": 5000}
START_END_TOLERANCE_MS = 500


def frame_to_ms(frame: int, fps: float) -> int:
    """Única conversión frame→ms del laboratorio."""
    return round(frame * 1000 / fps)


def violation_intervals(states: list, fps: float) -> list[dict]:
    """Corridas contiguas de violación (estado False). True y None cortan.

    end_ms es el instante del primer frame posterior a la corrida (si la
    corrida llega al final, el fin del timeline) — borde exclusivo.
    """
    intervals = []
    run_start = None
    for frame, state in enumerate(states):
        if state is False:
            if run_start is None:
                run_start = frame
        elif run_start is not None:
            intervals.append(
                {"start_ms": frame_to_ms(run_start, fps), "end_ms": frame_to_ms(frame, fps)}
            )
            run_start = None
    if run_start is not None:
        intervals.append(
            {"start_ms": frame_to_ms(run_start, fps), "end_ms": frame_to_ms(len(states), fps)}
        )
    return intervals


def track_condition_intervals(track: dict, end_frame: int, fps: float) -> list[dict]:
    """Intervalos de violación de un track para cada condición CR."""
    out = []
    for condition_id, attr in CONDITIONS.items():
        states = attribute_states(track, attr, end_frame)
        for iv in violation_intervals(states, fps):
            out.append({"condition_id": condition_id, "track_id": track["track_id"], **iv})
    return out
```

- [ ] **Step 4: Verificar que pasa**

Run: `python3 -m pytest datasets/tests/test_derive_clip_gt.py -q` → `4 passed`

- [ ] **Step 5: Checkpoint** — `python3 -m pytest datasets/tests/ -q` en verde.

---

### Task 3: Derivación — fusión de escena, modo subject, clasificación y ensamble

**Files:**
- Modify: `datasets/scripts/videogt/derive_clip_gt.py` (agregar funciones)
- Test: `datasets/tests/test_derive_clip_gt.py` (agregar tests)

**Interfaces:**
- Consumes: `track_condition_intervals`, `DEFAULT_PATTERN_SET_MS` (Task 2).
- Produces: `merge_scene_intervals(intervals: list[dict]) -> list[dict]` con
  `{"condition_id", "start_ms", "end_ms", "subjects_in_evidence": int}`;
  `classify_intervals(intervals, pattern_set_ms) -> tuple[list, list]`
  (episodios, sub-umbral); `subject_labels(tracks) -> dict[int, str]`
  (`persona_A`, `persona_B`, … por track_id ascendente);
  `assemble_clip_gt(clip_meta: dict, clip_info: dict, episodes: list,
  sub_events: list) -> dict` — el JSON `clip_gt.v2` completo. Task 4 (CLI) y
  Task 6 (compare) consumen el JSON resultante.

- [ ] **Step 1: Tests que fallan (agregar al archivo existente)**

```python
from videogt.derive_clip_gt import (
    assemble_clip_gt,
    classify_intervals,
    merge_scene_intervals,
    subject_labels,
)


def _iv(cond, start, end, track=0):
    return {"condition_id": cond, "track_id": track, "start_ms": start, "end_ms": end}


def test_merge_scene_fusiona_solapes_de_misma_condicion():
    merged = merge_scene_intervals([
        _iv("CR-01", 1000, 5000, track=0),
        _iv("CR-01", 4000, 9000, track=1),   # solapa → fusión
        _iv("CR-01", 12000, 13000, track=0), # separado
        _iv("CR-02", 2000, 8000, track=1),   # otra condición, no fusiona
    ])
    assert merged == [
        {"condition_id": "CR-01", "start_ms": 1000, "end_ms": 9000, "subjects_in_evidence": 2},
        {"condition_id": "CR-01", "start_ms": 12000, "end_ms": 13000, "subjects_in_evidence": 1},
        {"condition_id": "CR-02", "start_ms": 2000, "end_ms": 8000, "subjects_in_evidence": 1},
    ]


def test_classify_separa_episodios_de_subumbral():
    episodes, sub = classify_intervals(
        [
            {"condition_id": "CR-01", "start_ms": 0, "end_ms": 4000, "subjects_in_evidence": 1},
            {"condition_id": "CR-01", "start_ms": 8000, "end_ms": 9000, "subjects_in_evidence": 1},
        ],
        {"CR-01": 3000, "CR-02": 5000},
    )
    assert len(episodes) == 1 and episodes[0]["end_ms"] == 4000
    assert len(sub) == 1 and "persistencia" in sub[0]["reason"]


def test_subject_labels_ordena_por_track_id():
    tracks = [{"track_id": 7}, {"track_id": 2}]
    assert subject_labels(tracks) == {2: "persona_A", 7: "persona_B"}


def test_assemble_clip_gt_completo():
    clip_meta = {
        "clip_id": "cb_a01_p1_cr01", "block": "A", "scenario": "P1",
        "level": "scene",
        "recording": {"resolution": "1280x720", "distance_band_m": "5-10",
                      "lighting": "natural", "occlusion": "low"},
        "annotation": {"annotator": "a1", "double_annotated": False},
    }
    clip_info = {"fps": 30, "duration_ms": 32000, "file": "clips/cb_a01_p1_cr01.mp4"}
    episodes = [{"condition_id": "CR-01", "start_ms": 4200, "end_ms": 21500,
                 "subjects_in_evidence": 1}]
    gt = assemble_clip_gt(clip_meta, clip_info, episodes, sub_events=[])
    assert gt["schema_version"] == "clip_gt.v2"
    assert gt["negative"] is False
    assert gt["episodes"][0]["id"] == "ep1"
    assert gt["episodes"][0]["level"] == "scene"
    assert gt["duration_ms"] == 32000
    assert gt["annotation"]["start_end_tolerance_ms"] == 500
    # negativo ⇔ sin episodios
    gt_neg = assemble_clip_gt(clip_meta, clip_info, [], [])
    assert gt_neg["negative"] is True and gt_neg["episodes"] == []


def test_assemble_nota_condicion_activa_al_final():
    clip_meta = {"clip_id": "x", "block": "A", "scenario": "P1", "level": "scene",
                 "recording": {}, "annotation": {"annotator": "a1"}}
    clip_info = {"fps": 30, "duration_ms": 10000, "file": "clips/x.mp4"}
    gt = assemble_clip_gt(clip_meta, clip_info,
                          [{"condition_id": "CR-01", "start_ms": 2000, "end_ms": 10000,
                            "subjects_in_evidence": 1}], [])
    assert "final del clip" in gt["episodes"][0]["notes"]
```

- [ ] **Step 2: Verificar fallo** — `ImportError` sobre `merge_scene_intervals`.

- [ ] **Step 3: Implementación (agregar a `derive_clip_gt.py`)**

```python
def merge_scene_intervals(intervals: list[dict]) -> list[dict]:
    """Fusiona intervalos solapados de la MISMA condición entre tracks (G0).

    El validador exige "sin solape de la misma condición" a nivel escena;
    subjects_in_evidence = máximo de sujetos concurrentes (barrido de eventos).
    """
    merged = []
    for condition_id in sorted({iv["condition_id"] for iv in intervals}):
        group = sorted(
            (iv for iv in intervals if iv["condition_id"] == condition_id),
            key=lambda iv: iv["start_ms"],
        )
        cluster: list[dict] = []
        for iv in group:
            if cluster and iv["start_ms"] <= cluster[-1]["_end"]:
                cluster[-1]["_members"].append(iv)
                cluster[-1]["_end"] = max(cluster[-1]["_end"], iv["end_ms"])
            else:
                cluster.append({"_members": [iv], "_end": iv["end_ms"]})
        for c in cluster:
            events = []
            for m in c["_members"]:
                events.append((m["start_ms"], 1))
                events.append((m["end_ms"], -1))
            concurrent = peak = 0
            for _, delta in sorted(events):
                concurrent += delta
                peak = max(peak, concurrent)
            merged.append({
                "condition_id": condition_id,
                "start_ms": min(m["start_ms"] for m in c["_members"]),
                "end_ms": c["_end"],
                "subjects_in_evidence": peak,
            })
    merged.sort(key=lambda iv: (iv["condition_id"], iv["start_ms"]))
    return merged


def classify_intervals(intervals: list[dict], pattern_set_ms: dict) -> tuple[list, list]:
    """Separa episodios (duración ≥ persistencia mínima) de eventos sub-umbral."""
    episodes, sub_events = [], []
    for iv in intervals:
        duration = iv["end_ms"] - iv["start_ms"]
        minimum = pattern_set_ms[iv["condition_id"]]
        if duration >= minimum:
            episodes.append(dict(iv))
        else:
            sub_events.append({
                "condition_id": iv["condition_id"],
                "start_ms": iv["start_ms"],
                "end_ms": iv["end_ms"],
                "reason": (
                    f"transitorio < persistencia mínima "
                    f"({duration} ms < {minimum} ms) — NO debe alertar"
                ),
            })
    return episodes, sub_events


def subject_labels(tracks: list[dict]) -> dict[int, str]:
    """track_id → persona_A, persona_B, … (orden por track_id, spec 43 §4.3)."""
    ordered = sorted(t["track_id"] for t in tracks)
    return {tid: f"persona_{chr(65 + i)}" for i, tid in enumerate(ordered)}


def assemble_clip_gt(clip_meta: dict, clip_info: dict,
                     episodes: list[dict], sub_events: list[dict]) -> dict:
    """Ensambla el JSON clip_gt.v2 (schema del spec 43 §4, sin cambios)."""
    level = clip_meta.get("level", "scene")
    duration_ms = clip_info["duration_ms"]
    out_episodes = []
    for i, ep in enumerate(sorted(episodes, key=lambda e: (e["start_ms"], e["condition_id"]))):
        notes = ep.get("notes", "")
        if ep["end_ms"] >= duration_ms:
            suffix = "la condición sigue activa al final del clip"
            notes = f"{notes}; {suffix}" if notes else suffix
        entry = {
            "id": f"ep{i + 1}",
            "condition_id": ep["condition_id"],
            "level": level,
            "start_ms": ep["start_ms"],
            "end_ms": ep["end_ms"],
            "subjects_in_evidence": ep["subjects_in_evidence"],
            "notes": notes,
        }
        if level == "subject":
            entry["subject_label"] = ep["subject_label"]
        out_episodes.append(entry)

    annotation = dict(clip_meta.get("annotation", {}))
    annotation.setdefault("double_annotated", False)
    annotation.setdefault("second_annotator", None)
    annotation.setdefault("kappa", None)
    annotation["start_end_tolerance_ms"] = START_END_TOLERANCE_MS

    return {
        "schema_version": "clip_gt.v2",
        "clip_id": clip_meta["clip_id"],
        "source_file": clip_info["file"],
        "block": clip_meta["block"],
        "scenario": clip_meta["scenario"],
        "fps_nominal": clip_info["fps"],
        "duration_ms": duration_ms,
        "recording": clip_meta.get("recording", {}),
        "negative": len(out_episodes) == 0,
        "episodes": out_episodes,
        "sub_threshold_events": sub_events,
        "annotation": annotation,
    }
```

- [ ] **Step 4: Verificar que pasa** — `python3 -m pytest datasets/tests/test_derive_clip_gt.py -q`

- [ ] **Step 5: Checkpoint** — suite completa en verde.

---

### Task 4: CLI de derivación (`derive_clip_gt.py main`)

**Files:**
- Modify: `datasets/scripts/videogt/derive_clip_gt.py` (agregar `derive` + `main`)
- Test: `datasets/tests/test_derive_clip_gt.py` (agregar test end-to-end)

**Interfaces:**
- Consumes: todo lo anterior + `parse_cvat_video_xml` (Task 1).
- Produces: `derive(xml_path, clip_yaml_path, info_json_path,
  pattern_set_ms) -> dict` (el clip_gt.v2) y CLI
  `python3 datasets/scripts/videogt/derive_clip_gt.py --xml F --clip-yaml F
  --info F --out F [--pattern-set "CR-01=3000,CR-02=5000"]` que además
  imprime el timeline por track/condición para revisión humana.
- Formato `clip.yaml` (spec §4.2): claves `clip_id, block, scenario, level,
  recording{...}, annotation{annotator, double_annotated}`.
- Formato `<clip_id>.info.json` (lo emite Task 7): claves
  `{"clip_id", "file", "fps", "duration_ms", "n_frames", "resolution", "sha256"}`.

- [ ] **Step 1: Test end-to-end que falla**

```python
import json
import textwrap

from videogt.derive_clip_gt import derive

E2E_XML = textwrap.dedent("""\
    <annotations>
      <version>1.1</version>
      <meta><task><size>300</size></task></meta>
      <track id="0" label="person">
        <box frame="0" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="60" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="210" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="240" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">false</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
        <box frame="270" keyframe="1" outside="0" occluded="0" xtl="0" ytl="0" xbr="9" ybr="9">
          <attribute name="has_helmet">true</attribute>
          <attribute name="has_vest">true</attribute>
        </box>
      </track>
    </annotations>
""")

CLIP_YAML = textwrap.dedent("""\
    clip_id: cb_lab_p1
    block: A
    scenario: P1
    level: scene
    recording:
      resolution: 1280x720
      distance_band_m: "5-10"
      lighting: natural
      occlusion: low
    annotation:
      annotator: a1
      double_annotated: false
""")


def test_derive_end_to_end(tmp_path):
    xml = tmp_path / "a.xml"; xml.write_text(E2E_XML)
    cy = tmp_path / "clip.yaml"; cy.write_text(CLIP_YAML)
    info = tmp_path / "clip.info.json"
    info.write_text(json.dumps({
        "clip_id": "cb_lab_p1", "file": "clips/cb_lab_p1.mp4", "fps": 30,
        "duration_ms": 10000, "n_frames": 300, "resolution": "1280x720",
        "sha256": "0" * 64,
    }))
    gt = derive(xml, cy, info, {"CR-01": 3000, "CR-02": 5000})
    # frames 60-209 sin casco a 30fps = 2000-7000ms → episodio (5000ms ≥ 3000)
    # frames 240-269 = 8000-9000ms = 1000ms < 3000 → sub-umbral
    assert len(gt["episodes"]) == 1
    assert gt["episodes"][0] == {
        "id": "ep1", "condition_id": "CR-01", "level": "scene",
        "start_ms": 2000, "end_ms": 7000, "subjects_in_evidence": 1, "notes": "",
    }
    assert len(gt["sub_threshold_events"]) == 1
    assert gt["sub_threshold_events"][0]["start_ms"] == 8000
    assert gt["negative"] is False
```

- [ ] **Step 2: Verificar fallo** — `ImportError: cannot import name 'derive'`.

- [ ] **Step 3: Implementación (agregar a `derive_clip_gt.py`)**

```python
import argparse
import json

import yaml


def _parse_pattern_set(text: str) -> dict:
    """'CR-01=3000,CR-02=5000' → {'CR-01': 3000, 'CR-02': 5000}."""
    out = dict(DEFAULT_PATTERN_SET_MS)
    for part in filter(None, (p.strip() for p in text.split(","))):
        key, _, value = part.partition("=")
        out[key.strip()] = int(value)
    return out


def _fmt_ms(ms: int) -> str:
    return f"{ms // 60000:02d}:{(ms % 60000) / 1000:06.3f}"


def derive(xml_path, clip_yaml_path, info_json_path, pattern_set_ms: dict) -> dict:
    """Pipeline completo: XML corregido + clip.yaml + info.json → clip_gt.v2."""
    from videogt.cvat_xml import parse_cvat_video_xml

    doc = parse_cvat_video_xml(xml_path)
    clip_meta = yaml.safe_load(Path(clip_yaml_path).read_text())
    clip_info = json.loads(Path(info_json_path).read_text())
    fps = clip_info["fps"]
    end_frame = clip_info["n_frames"] - 1
    if doc["stop_frame"] is not None:
        end_frame = min(end_frame, doc["stop_frame"])

    persons = [t for t in doc["tracks"] if t["label"] == "person"]
    raw = [iv for t in persons for iv in track_condition_intervals(t, end_frame, fps)]

    level = clip_meta.get("level", "scene")
    if level == "subject":
        labels = subject_labels(persons)
        intervals = [
            {**iv, "subjects_in_evidence": 1, "subject_label": labels[iv["track_id"]]}
            for iv in raw
        ]
    else:
        intervals = merge_scene_intervals(raw)

    episodes, sub_events = classify_intervals(intervals, pattern_set_ms)
    return assemble_clip_gt(clip_meta, clip_info, episodes, sub_events)


def _print_timeline(gt: dict) -> None:
    """Timeline legible para la revisión final humana contra el video."""
    print(f"\n=== {gt['clip_id']}  ({_fmt_ms(gt['duration_ms'])}, "
          f"{gt['fps_nominal']} fps, negative={gt['negative']}) ===")
    for ep in gt["episodes"]:
        who = ep.get("subject_label", f"{ep['subjects_in_evidence']} sujeto(s)")
        print(f"  EPISODIO {ep['id']:>4}  {ep['condition_id']}  "
              f"{_fmt_ms(ep['start_ms'])} → {_fmt_ms(ep['end_ms'])}  [{who}]"
              + (f"  // {ep['notes']}" if ep["notes"] else ""))
    for ev in gt["sub_threshold_events"]:
        print(f"  sub-umbral      {ev['condition_id']}  "
              f"{_fmt_ms(ev['start_ms'])} → {_fmt_ms(ev['end_ms'])}  ({ev['reason']})")
    print("Revisar contra el video antes de promover al banco.\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", required=True, help="CVAT XML corregido")
    parser.add_argument("--clip-yaml", required=True, help="metadata del clip (spec §4.2)")
    parser.add_argument("--info", required=True, help="<clip_id>.info.json de prepare_clip.sh")
    parser.add_argument("--out", required=True, help="salida clip_gt.v2 JSON")
    parser.add_argument("--pattern-set", default="", help="ej: CR-01=3000,CR-02=5000")
    args = parser.parse_args(argv)

    gt = derive(args.xml, args.clip_yaml, args.info, _parse_pattern_set(args.pattern_set))
    Path(args.out).write_text(json.dumps(gt, indent=2, ensure_ascii=False) + "\n")
    _print_timeline(gt)
    print(f"GT escrito en {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verificar** — test e2e pasa; probar el CLI a mano con los mismos
  fixtures escritos a un tmp dir si se quiere.

- [ ] **Step 5: Checkpoint** — suite completa en verde.

---

### Task 5: Validador (`validate_clip_gt.py`, spec 43 §5)

**Files:**
- Create: `datasets/scripts/bench/validate_clip_gt.py`
- Test: `datasets/tests/test_validate_clip_gt.py`

**Interfaces:**
- Consumes: JSON `clip_gt.v2` (Task 3/4) y `manifest.yaml` del banco.
- Produces: `validate_gt(gt: dict) -> list[str]` (lista de errores, vacía =
  válido); `validate_manifest(manifest: dict, base_dir: Path) -> list[str]`;
  CLI `python3 datasets/scripts/bench/validate_clip_gt.py --gt-dir D
  [--manifest F]` con exit code 1 si hay errores.
- Formato `manifest.yaml`: `{"clips": [{"clip_id", "file", "sha256", "fps",
  "duration_ms", "resolution", "scenario", "block", "gt"}]}`.

- [ ] **Step 1: Tests que fallan**

```python
# datasets/tests/test_validate_clip_gt.py
"""Validador de clip_gt.v2 (spec 43 §5) — fixtures sintéticos."""
import copy

from bench.validate_clip_gt import validate_gt, validate_manifest

VALID_GT = {
    "schema_version": "clip_gt.v2",
    "clip_id": "cb_a01_p1_cr01",
    "source_file": "clips/cb_a01_p1_cr01.mp4",
    "block": "A",
    "scenario": "P1",
    "fps_nominal": 30,
    "duration_ms": 32000,
    "recording": {"resolution": "1280x720", "distance_band_m": "5-10",
                  "lighting": "natural", "occlusion": "low"},
    "negative": False,
    "episodes": [
        {"id": "ep1", "condition_id": "CR-01", "level": "scene",
         "start_ms": 4200, "end_ms": 21500, "subjects_in_evidence": 1, "notes": ""},
    ],
    "sub_threshold_events": [],
    "annotation": {"annotator": "a1", "double_annotated": False,
                   "second_annotator": None, "kappa": None,
                   "start_end_tolerance_ms": 500},
}


def test_gt_valido_sin_errores():
    assert validate_gt(copy.deepcopy(VALID_GT)) == []


def test_detecta_episodio_fuera_de_duracion():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"][0]["end_ms"] = 99000
    assert any("duration_ms" in e for e in validate_gt(gt))


def test_detecta_solape_de_misma_condicion():
    gt = copy.deepcopy(VALID_GT)
    gt["episodes"].append({"id": "ep2", "condition_id": "CR-01", "level": "scene",
                           "start_ms": 20000, "end_ms": 25000,
                           "subjects_in_evidence": 1, "notes": ""})
    assert any("solape" in e for e in validate_gt(gt))


def test_solape_permitido_entre_sujetos_distintos():
    gt = copy.deepcopy(VALID_GT)
    for ep, label in zip(gt["episodes"], ["persona_A"]):
        ep["level"] = "subject"; ep["subject_label"] = label
    gt["episodes"].append({"id": "ep2", "condition_id": "CR-01", "level": "subject",
                           "subject_label": "persona_B", "start_ms": 5000,
                           "end_ms": 20000, "subjects_in_evidence": 1, "notes": ""})
    assert validate_gt(gt) == []


def test_detecta_negative_inconsistente():
    gt = copy.deepcopy(VALID_GT)
    gt["negative"] = True
    assert any("negative" in e for e in validate_gt(gt))


def test_manifest_cruza_gt_y_checksum(tmp_path):
    gt_dir = tmp_path / "gt"; gt_dir.mkdir()
    clips = tmp_path / "clips"; clips.mkdir()
    (clips / "c1.mp4").write_bytes(b"fake video bytes")
    import hashlib, json
    sha = hashlib.sha256(b"fake video bytes").hexdigest()
    gt = copy.deepcopy(VALID_GT)
    gt["clip_id"] = "c1"; gt["source_file"] = "clips/c1.mp4"
    (gt_dir / "c1.json").write_text(json.dumps(gt))
    manifest = {"clips": [{"clip_id": "c1", "file": "clips/c1.mp4", "sha256": sha,
                           "fps": 30, "duration_ms": 32000, "resolution": "1280x720",
                           "scenario": "P1", "block": "A", "gt": "gt/c1.json"}]}
    assert validate_manifest(manifest, tmp_path) == []
    manifest["clips"][0]["sha256"] = "f" * 64
    assert any("sha256" in e for e in validate_manifest(manifest, tmp_path))
```

- [ ] **Step 2: Verificar fallo** — `No module named 'bench.validate_clip_gt'`.
  (Antes de correr: revisar cómo importa `datasets/tests/test_person_gt.py`
  y replicar EXACTAMENTE ese patrón de import — `pythonpath` es
  `datasets/scripts`, así que la forma esperada es
  `from bench.validate_clip_gt import ...`.)

- [ ] **Step 3: Implementación**

```python
# datasets/scripts/bench/validate_clip_gt.py
"""Valida clip_gt.v2 y su cruce con manifest.yaml (spec 43 §5).

Chequea: schema y campos requeridos, episodios dentro de duration_ms,
sin solape de la misma condición (por sujeto en nivel subject),
negative ⇔ sin episodios, y manifest ↔ archivos ↔ sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

_REQUIRED_TOP = ["schema_version", "clip_id", "source_file", "block", "scenario",
                 "fps_nominal", "duration_ms", "recording", "negative",
                 "episodes", "sub_threshold_events", "annotation"]
_REQUIRED_EP = ["id", "condition_id", "level", "start_ms", "end_ms",
                "subjects_in_evidence", "notes"]
_BLOCKS = {"A", "B", "C"}
_CONDITIONS = {"CR-01", "CR-02"}


def validate_gt(gt: dict) -> list[str]:
    """Devuelve la lista de errores del GT (vacía si es válido)."""
    errors = []
    for key in _REQUIRED_TOP:
        if key not in gt:
            errors.append(f"falta campo requerido '{key}'")
    if errors:
        return errors
    cid = gt["clip_id"]
    if gt["schema_version"] != "clip_gt.v2":
        errors.append(f"{cid}: schema_version != clip_gt.v2")
    if gt["block"] not in _BLOCKS:
        errors.append(f"{cid}: block '{gt['block']}' fuera de {sorted(_BLOCKS)}")
    if gt["negative"] != (len(gt["episodes"]) == 0):
        errors.append(f"{cid}: negative debe ser equivalente a 'sin episodios'")

    for ep in gt["episodes"]:
        for key in _REQUIRED_EP:
            if key not in ep:
                errors.append(f"{cid}/{ep.get('id', '?')}: falta '{key}'")
        if ep.get("condition_id") not in _CONDITIONS:
            errors.append(f"{cid}/{ep.get('id')}: condition_id inválido")
        if ep.get("level") == "subject" and not ep.get("subject_label"):
            errors.append(f"{cid}/{ep.get('id')}: level subject sin subject_label")
        start, end = ep.get("start_ms", 0), ep.get("end_ms", 0)
        if not (0 <= start < end):
            errors.append(f"{cid}/{ep.get('id')}: start_ms/end_ms inválidos")
        if end > gt["duration_ms"]:
            errors.append(f"{cid}/{ep.get('id')}: end_ms excede duration_ms")

    # solape de la misma condición (misma persona si level=subject)
    def _key(ep):
        return (ep["condition_id"], ep.get("subject_label")) \
            if ep.get("level") == "subject" else (ep["condition_id"], None)

    groups: dict = {}
    for ep in gt["episodes"]:
        groups.setdefault(_key(ep), []).append(ep)
    for (condition, subject), eps in groups.items():
        eps = sorted(eps, key=lambda e: e["start_ms"])
        for prev, cur in zip(eps, eps[1:]):
            if cur["start_ms"] < prev["end_ms"]:
                who = f" ({subject})" if subject else ""
                errors.append(f"{cid}: solape de {condition}{who}: "
                              f"{prev['id']} y {cur['id']}")
    return errors


def validate_manifest(manifest: dict, base_dir: Path) -> list[str]:
    """Cruza manifest.yaml contra archivos de GT y checksums de media.

    La media puede no estar presente (git-ignored): en ese caso el checksum
    no se verifica y se informa como advertencia por stdout, no como error.
    """
    errors = []
    for row in manifest.get("clips", []):
        cid = row.get("clip_id", "?")
        gt_path = base_dir / row["gt"]
        if not gt_path.exists():
            errors.append(f"{cid}: falta el GT {row['gt']}")
            continue
        gt = json.loads(gt_path.read_text())
        gt_errors = validate_gt(gt)
        errors.extend(gt_errors)
        if gt.get("clip_id") != cid:
            errors.append(f"{cid}: clip_id del GT no coincide ({gt.get('clip_id')})")
        media = base_dir / row["file"]
        if media.exists():
            digest = hashlib.sha256(media.read_bytes()).hexdigest()
            if digest != row.get("sha256"):
                errors.append(f"{cid}: sha256 no coincide con manifest")
        else:
            print(f"[aviso] {cid}: media ausente ({row['file']}) — checksum no verificado")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt-dir", help="directorio con clip_gt.v2 *.json")
    parser.add_argument("--manifest", help="manifest.yaml del banco")
    parser.add_argument("--base-dir", default=".",
                        help="base para rutas del manifest (default: cwd)")
    args = parser.parse_args(argv)

    errors = []
    if args.gt_dir:
        for path in sorted(Path(args.gt_dir).glob("*.json")):
            errors.extend(validate_gt(json.loads(path.read_text())))
    if args.manifest:
        manifest = yaml.safe_load(Path(args.manifest).read_text())
        errors.extend(validate_manifest(manifest, Path(args.base_dir)))

    for e in errors:
        print(f"ERROR: {e}")
    print(f"{'✗' if errors else '✓'} validate_clip_gt: {len(errors)} error(es)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verificar que pasa** — `python3 -m pytest datasets/tests/test_validate_clip_gt.py -q`

- [ ] **Step 5: Checkpoint** — suite completa en verde.

---

### Task 6: Doble anotación (`compare_annotations.py`)

**Files:**
- Create: `datasets/scripts/videogt/compare_annotations.py`
- Test: `datasets/tests/test_compare_annotations.py`

**Interfaces:**
- Consumes: dos JSON `clip_gt.v2` del mismo clip (Task 4).
- Produces: `window_states(gt: dict, condition_id: str, window_ms=1000) ->
  list[bool]` (estado por ventana, muestreo en el punto medio);
  `cohen_kappa(a: list[bool], b: list[bool]) -> float`;
  `compare(gt_a: dict, gt_b: dict) -> dict` con claves `kappa_global`,
  `kappa_por_condicion: {str: float}`, `median_abs_dstart_ms`,
  `median_abs_dend_ms`, `unpaired_a`, `unpaired_b`. CLI:
  `python3 .../compare_annotations.py --a gt_a.json --b gt_b.json`.

- [ ] **Step 1: Tests que fallan**

```python
# datasets/tests/test_compare_annotations.py
"""Kappa de Cohen por ventana de 1 s + deltas de bordes (spec 43 §4.2)."""
from videogt.compare_annotations import cohen_kappa, compare, window_states


def _gt(episodes, duration_ms=10000):
    return {"schema_version": "clip_gt.v2", "clip_id": "c", "duration_ms": duration_ms,
            "episodes": episodes, "sub_threshold_events": []}


def _ep(cond, start, end):
    return {"id": "e", "condition_id": cond, "level": "scene",
            "start_ms": start, "end_ms": end, "subjects_in_evidence": 1, "notes": ""}


def test_window_states_muestrea_punto_medio():
    gt = _gt([_ep("CR-01", 1400, 3600)])
    # ventanas [0,1s):midpoint 500→F, [1,2s):1500→T, [2,3s):2500→T, [3,4s):3500→T, resto F
    assert window_states(gt, "CR-01")[:5] == [False, True, True, True, False]
    assert len(window_states(gt, "CR-01")) == 10


def test_cohen_kappa_extremos():
    a = [True, True, False, False]
    assert cohen_kappa(a, a) == 1.0
    assert cohen_kappa(a, [not v for v in a]) < 0
    assert cohen_kappa([True, False], [True, True]) == 0.0


def test_compare_acuerdo_perfecto():
    gt = _gt([_ep("CR-01", 1000, 5000)])
    result = compare(gt, gt)
    assert result["kappa_global"] == 1.0
    assert result["median_abs_dstart_ms"] == 0
    assert result["unpaired_a"] == 0 and result["unpaired_b"] == 0


def test_compare_reporta_deltas_y_desapareados():
    a = _gt([_ep("CR-01", 1000, 5000), _ep("CR-02", 6000, 9000)])
    b = _gt([_ep("CR-01", 1400, 5300)])  # borde corrido, CR-02 no visto
    result = compare(a, b)
    assert result["median_abs_dstart_ms"] == 400
    assert result["median_abs_dend_ms"] == 300
    assert result["unpaired_a"] == 1 and result["unpaired_b"] == 0
    assert result["kappa_global"] < 1.0
```

- [ ] **Step 2: Verificar fallo.**

- [ ] **Step 3: Implementación**

```python
# datasets/scripts/videogt/compare_annotations.py
"""Compara dos clip_gt.v2 del mismo clip (doble anotación, spec 43 §4.2).

Kappa de Cohen sobre presencia de condición por ventana de 1 s (estado
muestreado en el punto medio de la ventana — determinístico y sin ambigüedad
de bordes) + |Δstart| y |Δend| medianos entre episodios apareados por máximo
solape (greedy, por condición).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from videogt.derive_clip_gt import CONDITIONS  # noqa: E402


def window_states(gt: dict, condition_id: str, window_ms: int = 1000) -> list[bool]:
    """Estado por ventana: True si algún episodio de la condición cubre el punto medio."""
    n_windows = -(-gt["duration_ms"] // window_ms)  # ceil
    episodes = [e for e in gt["episodes"] if e["condition_id"] == condition_id]
    states = []
    for w in range(n_windows):
        mid = w * window_ms + window_ms // 2
        states.append(any(e["start_ms"] <= mid < e["end_ms"] for e in episodes))
    return states


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    """Kappa de Cohen binario. Si pe == 1 (marginales degeneradas): 1.0 si hay
    acuerdo total, 0.0 si no (convención documentada del laboratorio)."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def _pair_episodes(eps_a: list[dict], eps_b: list[dict]) -> tuple[list, int, int]:
    """Apareo greedy por máximo solape dentro de cada condición."""
    pairs = []
    used_b: set[int] = set()
    for ea in eps_a:
        best, best_overlap = None, 0
        for j, eb in enumerate(eps_b):
            if j in used_b or eb["condition_id"] != ea["condition_id"]:
                continue
            overlap = min(ea["end_ms"], eb["end_ms"]) - max(ea["start_ms"], eb["start_ms"])
            if overlap > best_overlap:
                best, best_overlap = j, overlap
        if best is not None:
            used_b.add(best)
            pairs.append((ea, eps_b[best]))
    unpaired_a = len(eps_a) - len(pairs)
    unpaired_b = len(eps_b) - len(used_b)
    return pairs, unpaired_a, unpaired_b


def compare(gt_a: dict, gt_b: dict) -> dict:
    """Resultado completo de la comparación entre dos anotadores."""
    kappa_by = {}
    all_a: list[bool] = []
    all_b: list[bool] = []
    for condition_id in CONDITIONS:
        sa = window_states(gt_a, condition_id)
        sb = window_states(gt_b, condition_id)
        kappa_by[condition_id] = round(cohen_kappa(sa, sb), 4)
        all_a.extend(sa)
        all_b.extend(sb)

    pairs, unpaired_a, unpaired_b = _pair_episodes(gt_a["episodes"], gt_b["episodes"])
    dstarts = [abs(x["start_ms"] - y["start_ms"]) for x, y in pairs]
    dends = [abs(x["end_ms"] - y["end_ms"]) for x, y in pairs]
    return {
        "clip_id": gt_a.get("clip_id"),
        "kappa_global": round(cohen_kappa(all_a, all_b), 4),
        "kappa_por_condicion": kappa_by,
        "median_abs_dstart_ms": statistics.median(dstarts) if dstarts else None,
        "median_abs_dend_ms": statistics.median(dends) if dends else None,
        "episodios_apareados": len(pairs),
        "unpaired_a": unpaired_a,
        "unpaired_b": unpaired_b,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True, help="clip_gt.v2 del anotador A")
    parser.add_argument("--b", required=True, help="clip_gt.v2 del anotador B")
    args = parser.parse_args(argv)
    gt_a = json.loads(Path(args.a).read_text())
    gt_b = json.loads(Path(args.b).read_text())
    if gt_a.get("clip_id") != gt_b.get("clip_id"):
        print("ERROR: los GT no son del mismo clip")
        return 1
    print(json.dumps(compare(gt_a, gt_b), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verificar que pasa.**

- [ ] **Step 5: Checkpoint** — suite datasets completa en verde:
  `python3 -m pytest datasets/tests/ -q`

---

### Task 7: Etapa 0 — `prepare_clip.sh`, labels CVAT y laboratorio

**Files:**
- Create: `datasets/scripts/videogt/prepare_clip.sh`
- Create: `datasets/scripts/videogt/cvat_labels.json`
- Create: `datasets-videos/README.md`, `datasets-videos/.gitignore`

**Interfaces:**
- Produces: `datasets-videos/clips/<clip_id>.mp4` (CFR, sin audio) +
  `<clip_id>.info.json` con `{"clip_id", "file", "fps", "duration_ms",
  "n_frames", "resolution", "sha256"}` — lo consumen Tasks 4 y 10.

- [ ] **Step 1: Script**

```bash
#!/usr/bin/env bash
# datasets/scripts/videogt/prepare_clip.sh
# Etapa 0 del video-gt-lab: normaliza un video fuente a CFR sin audio y emite
# <clip_id>.info.json (los videos de celular suelen ser VFR, que rompe el
# mapeo frame<->ms del pipeline). TODO lo que entra a CVAT pasa por acá.
#
# Uso: prepare_clip.sh <input> <clip_id> [--ss T] [--to T] [--fps N] [--scale WxH]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_DIR="$REPO_ROOT/datasets-videos/clips"

INPUT="${1:?uso: prepare_clip.sh <input> <clip_id> [--ss T] [--to T] [--fps N] [--scale WxH]}"
CLIP_ID="${2:?falta clip_id}"
shift 2
SS="" TO="" FPS=30 SCALE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ss) SS="$2"; shift 2 ;;
    --to) TO="$2"; shift 2 ;;
    --fps) FPS="$2"; shift 2 ;;
    --scale) SCALE="$2"; shift 2 ;;
    *) echo "opción desconocida: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/$CLIP_ID.mp4"

FILTERS="fps=$FPS"
[[ -n "$SCALE" ]] && FILTERS="$FILTERS,scale=${SCALE/x/:}"

ARGS=(-y -hide_banner -loglevel error)
[[ -n "$SS" ]] && ARGS+=(-ss "$SS")
ARGS+=(-i "$INPUT")
[[ -n "$TO" ]] && ARGS+=(-to "$TO")
ARGS+=(-an -vf "$FILTERS" -fps_mode cfr -c:v libx264 -crf 18 -preset medium "$OUT")
ffmpeg "${ARGS[@]}"

read -r WIDTH HEIGHT NFRAMES < <(ffprobe -v error -select_streams v:0 -count_frames \
  -show_entries stream=width,height,nb_read_frames -of csv=p=0 "$OUT" | tr ',' ' ')
SHA256=$(sha256sum "$OUT" | cut -d' ' -f1)
DURATION_MS=$(python3 -c "print(round($NFRAMES * 1000 / $FPS))")

python3 - "$OUT_DIR/$CLIP_ID.info.json" <<EOF
import json, sys
json.dump({
    "clip_id": "$CLIP_ID",
    "file": "clips/$CLIP_ID.mp4",
    "fps": $FPS,
    "duration_ms": $DURATION_MS,
    "n_frames": $NFRAMES,
    "resolution": "${WIDTH}x${HEIGHT}",
    "sha256": "$SHA256",
}, open(sys.argv[1], "w"), indent=2)
print(f"✓ {sys.argv[1]}")
EOF
echo "✓ $OUT  (${WIDTH}x${HEIGHT}, $FPS fps CFR, $NFRAMES frames, ${DURATION_MS} ms)"
```

- [ ] **Step 2: Config de labels CVAT (reproducibilidad del setup)**

```json
[
  {
    "name": "person",
    "type": "rectangle",
    "attributes": [
      {"name": "has_helmet", "mutable": true, "input_type": "checkbox",
       "default_value": "false", "values": ["false"]},
      {"name": "has_vest", "mutable": true, "input_type": "checkbox",
       "default_value": "false", "values": ["false"]}
    ]
  }
]
```

Guardar en `datasets/scripts/videogt/cvat_labels.json` (se pega en
"Raw" al crear el proyecto CVAT).

- [ ] **Step 3: Laboratorio `datasets-videos/`**

`datasets-videos/.gitignore`:

```gitignore
# media y artefactos regenerables del laboratorio — nunca commitear
raw/
clips/
preann/
corrected/
gt/
*.mp4
```

`datasets-videos/README.md`: describir el flujo por etapas con los comandos
reales (prepare → preannotate en media-plane → CVAT → derive → validate),
apuntando al spec `docs/superpowers/specs/2026-07-11-video-gt-lab-design.md`
y al protocolo de corrección (§5 del spec). Crear subdirs
`raw/ clips/ preann/ corrected/ gt/` y mover `recorte-1.mp4` a `raw/`.

- [ ] **Step 4: Smoke de la etapa 0 con recorte-1**

```bash
cd /home/simonll4/projects/e-ovrt_datasets
chmod +x datasets/scripts/videogt/prepare_clip.sh
mkdir -p datasets-videos/{raw,clips,preann,corrected,gt}
mv datasets-videos/recorte-1.mp4 datasets-videos/raw/
datasets/scripts/videogt/prepare_clip.sh datasets-videos/raw/recorte-1.mp4 lab_recorte1
cat datasets-videos/clips/lab_recorte1.info.json
```

Expected: `lab_recorte1.mp4` CFR 30 fps sin audio + info.json con sha256,
n_frames ≈ 733, duration_ms ≈ 24433.

- [ ] **Step 5: Checkpoint** — `git status` en e-ovrt_datasets muestra solo
  scripts/docs nuevos (nada de media); suite en verde.

---

### Task 8: media-plane — lógica pura de pre-anotación (`tools/videogt.py`)

**Files:**
- Create: `e-ovrt_media-plane/src/eovrt_media/tools/videogt.py`
- Test: `e-ovrt_media-plane/tests/tools/test_videogt.py`

**Interfaces:**
- Produces (tipos compartidos con Tasks 9-10): `Box = tuple[float, float,
  float, float]` (xyxy en px); `head_region(person: Box) -> Box` (tercio
  superior); `torso_region(person: Box) -> Box` (banda 20%–70% de la altura);
  `center_in(box: Box, region: Box) -> bool`;
  `infer_attributes(person: Box, helmets: list[Box], vests: list[Box]) ->
  dict[str, bool]` → `{"has_helmet": bool, "has_vest": bool}`;
  `smooth_bool(values: list[bool | None], window: int) -> list[bool | None]`
  (mayoría en ventana centrada, `None` pasa intacto y no vota);
  `thin_track(boxes: list[dict], eps_px: float) -> list[dict]` donde cada box
  es `{"frame": int, "box": Box, "attributes": dict}` — conserva primero,
  último, cambios de atributo y todo box cuya geometría difiera > eps del
  último conservado.

- [ ] **Step 1: Tests que fallan**

```python
# tests/tools/test_videogt.py
"""Lógica pura del video-gt-lab (sin GPU, sin modelos)."""
from eovrt_media.tools.videogt import (
    head_region,
    infer_attributes,
    smooth_bool,
    thin_track,
    torso_region,
)


def test_regiones_geometricas():
    person = (100.0, 0.0, 200.0, 300.0)
    assert head_region(person) == (100.0, 0.0, 200.0, 100.0)
    assert torso_region(person) == (100.0, 60.0, 200.0, 210.0)


def test_infer_attributes_asocia_por_centro():
    person = (100.0, 0.0, 200.0, 300.0)
    helmet_on_head = (130.0, 10.0, 170.0, 50.0)     # centro en tercio superior
    helmet_lejano = (400.0, 10.0, 440.0, 50.0)      # centro fuera de la persona
    vest_en_torso = (110.0, 80.0, 190.0, 180.0)
    assert infer_attributes(person, [helmet_on_head], []) == \
        {"has_helmet": True, "has_vest": False}
    assert infer_attributes(person, [helmet_lejano], [vest_en_torso]) == \
        {"has_helmet": False, "has_vest": True}


def test_smooth_bool_mata_parpadeo():
    values = [True, True, False, True, True]  # False aislado = parpadeo
    assert smooth_bool(values, window=3) == [True, True, True, True, True]
    con_none = [True, None, True, False, False, False]
    smoothed = smooth_bool(con_none, window=3)
    assert smoothed[1] is None            # None pasa intacto
    assert smoothed[4] is False           # tramo real de False sobrevive


def test_thin_track_conserva_lo_esencial():
    attrs_a = {"has_helmet": True, "has_vest": True}
    attrs_b = {"has_helmet": False, "has_vest": True}
    boxes = [
        {"frame": 0, "box": (0.0, 0.0, 10.0, 10.0), "attributes": attrs_a},
        {"frame": 3, "box": (1.0, 0.0, 11.0, 10.0), "attributes": attrs_a},   # ~igual → fuera
        {"frame": 6, "box": (2.0, 0.0, 12.0, 10.0), "attributes": attrs_b},   # cambia attr → queda
        {"frame": 9, "box": (50.0, 0.0, 60.0, 10.0), "attributes": attrs_b},  # salto geom → queda
        {"frame": 12, "box": (51.0, 0.0, 61.0, 10.0), "attributes": attrs_b}, # último → queda
    ]
    thinned = thin_track(boxes, eps_px=5.0)
    assert [b["frame"] for b in thinned] == [0, 6, 9, 12]
```

- [ ] **Step 2: Verificar fallo**

Run: `cd /home/simonll4/projects/e-ovrt_media-plane && source .venv/bin/activate && python -m pytest tests/tools/test_videogt.py -q`
Expected: FAIL — módulo inexistente.

- [ ] **Step 3: Implementación**

```python
# src/eovrt_media/tools/videogt.py
"""Lógica pura del video-gt-lab: asociación EPP→persona, suavizado temporal,
adelgazamiento de keyframes y escritura de CVAT for video 1.1.

Sin dependencias de torch/transformers — testeable sin GPU. La orquestación
con modelo y tracker vive en ``preannotate_video``.
"""
from __future__ import annotations

Box = tuple[float, float, float, float]


def head_region(person: Box) -> Box:
    """Tercio superior de la caja de persona (zona esperable del casco)."""
    x1, y1, x2, y2 = person
    return (x1, y1, x2, y1 + (y2 - y1) / 3)


def torso_region(person: Box) -> Box:
    """Banda 20%–70% de la altura (zona esperable del chaleco)."""
    x1, y1, x2, y2 = person
    h = y2 - y1
    return (x1, y1 + 0.2 * h, x2, y1 + 0.7 * h)


def center_in(box: Box, region: Box) -> bool:
    """True si el centro de ``box`` cae dentro de ``region``."""
    cx = (box[0] + box[2]) / 2
    cy = (box[1] + box[3]) / 2
    return region[0] <= cx <= region[2] and region[1] <= cy <= region[3]


def infer_attributes(person: Box, helmets: list[Box], vests: list[Box]) -> dict:
    """Inicializa has_helmet/has_vest por contención de centro en la región.

    Mismo criterio center-containment que ``bench.geometry`` del repo datasets:
    las cajas de EPP y las regiones tienen áreas muy distintas, IoU no sirve.
    """
    head = head_region(person)
    torso = torso_region(person)
    return {
        "has_helmet": any(center_in(h, head) for h in helmets),
        "has_vest": any(center_in(v, torso) for v in vests),
    }


def smooth_bool(values: list, window: int = 11) -> list:
    """Voto por mayoría en ventana centrada; None no vota y pasa intacto.

    Mata el parpadeo del detector para que el corrector humano vea
    transiciones reales, no ruido (spec video-gt-lab §3.1).
    """
    half = window // 2
    out = []
    for i, value in enumerate(values):
        if value is None:
            out.append(None)
            continue
        votes = [v for v in values[max(0, i - half):i + half + 1] if v is not None]
        out.append(sum(votes) * 2 >= len(votes))
    return out


def thin_track(boxes: list[dict], eps_px: float = 10.0) -> list[dict]:
    """Adelgaza keyframes: conserva primero, último, cambios de atributo y
    desviaciones geométricas > eps respecto del último conservado.

    CVAT interpola linealmente entre keyframes; eps acota el error de la caja
    interpolada. Un track detectado a 10 fps queda en decenas de keyframes.
    """
    if not boxes:
        return []
    kept = [boxes[0]]
    for box in boxes[1:-1]:
        last = kept[-1]
        moved = max(abs(a - b) for a, b in zip(box["box"], last["box"])) > eps_px
        if moved or box["attributes"] != last["attributes"]:
            kept.append(box)
    if len(boxes) > 1:
        kept.append(boxes[-1])
    return kept
```

- [ ] **Step 4: Verificar que pasa** — `python -m pytest tests/tools/test_videogt.py -q`

- [ ] **Step 5: Checkpoint** — `make test` y `make lint` en verde.

---

### Task 9: media-plane — writer CVAT for video 1.1

**Files:**
- Modify: `src/eovrt_media/tools/videogt.py` (agregar `build_cvat_xml`)
- Test: `tests/tools/test_videogt.py` (agregar tests)

**Interfaces:**
- Consumes: tracks adelgazados de Task 8.
- Produces: `build_cvat_xml(tracks: list[dict], stop_frame: int, width: int,
  height: int, task_name: str) -> str` — tracks:
  `{"track_id": int, "boxes": [{"frame", "box", "attributes"}]}`. Convención
  CVAT: agrega box de cierre `outside="1"` en `last_frame + 1` si el track
  termina antes de `stop_frame`. El XML resultante debe ser parseable por
  `videogt/cvat_xml.py` del repo datasets (mismo contrato §4.1 del spec).

- [ ] **Step 1: Tests que fallan (agregar)**

```python
import xml.etree.ElementTree as ET

from eovrt_media.tools.videogt import build_cvat_xml


def _track():
    return {"track_id": 0, "boxes": [
        {"frame": 0, "box": (10.0, 20.0, 110.0, 220.0),
         "attributes": {"has_helmet": True, "has_vest": False}},
        {"frame": 30, "box": (15.0, 20.0, 115.0, 220.0),
         "attributes": {"has_helmet": False, "has_vest": False}},
    ]}


def test_build_cvat_xml_estructura():
    xml = build_cvat_xml([_track()], stop_frame=99, width=1280, height=720,
                         task_name="lab_recorte1")
    root = ET.fromstring(xml)
    assert root.find("./meta/task/size").text == "100"
    (track,) = root.findall("track")
    assert track.get("label") == "person"
    boxes = track.findall("box")
    assert boxes[0].get("frame") == "0" and boxes[0].get("keyframe") == "1"
    attrs = {a.get("name"): a.text for a in boxes[0].findall("attribute")}
    assert attrs == {"has_helmet": "true", "has_vest": "false"}
    # cierre outside en last_frame + 1 (termina antes de stop_frame)
    assert boxes[-1].get("frame") == "31" and boxes[-1].get("outside") == "1"


def test_build_cvat_xml_sin_cierre_si_llega_al_final():
    track = _track()
    track["boxes"][-1]["frame"] = 99
    xml = build_cvat_xml([track], stop_frame=99, width=1280, height=720, task_name="t")
    boxes = ET.fromstring(xml).find("track").findall("box")
    assert boxes[-1].get("frame") == "99" and boxes[-1].get("outside") == "0"
```

- [ ] **Step 2: Verificar fallo.**

- [ ] **Step 3: Implementación (agregar a `videogt.py`)**

```python
import xml.etree.ElementTree as ET
from xml.dom import minidom


def build_cvat_xml(tracks: list[dict], stop_frame: int, width: int, height: int,
                   task_name: str) -> str:
    """Serializa tracks de persona al formato 'CVAT for video 1.1'.

    Convención CVAT: un track que termina antes del final del video se cierra
    con un box outside="1" en el frame siguiente al último visible.
    """
    root = ET.Element("annotations")
    ET.SubElement(root, "version").text = "1.1"
    task = ET.SubElement(ET.SubElement(root, "meta"), "task")
    ET.SubElement(task, "name").text = task_name
    ET.SubElement(task, "size").text = str(stop_frame + 1)
    original = ET.SubElement(task, "original_size")
    ET.SubElement(original, "width").text = str(width)
    ET.SubElement(original, "height").text = str(height)

    def _emit(parent, frame, box, attributes, outside):
        el = ET.SubElement(parent, "box", {
            "frame": str(frame), "keyframe": "1",
            "outside": "1" if outside else "0", "occluded": "0",
            "xtl": f"{box[0]:.2f}", "ytl": f"{box[1]:.2f}",
            "xbr": f"{box[2]:.2f}", "ybr": f"{box[3]:.2f}",
        })
        for name, value in attributes.items():
            attr = ET.SubElement(el, "attribute", {"name": name})
            attr.text = "true" if value else "false"

    for track in tracks:
        el = ET.SubElement(root, "track", {
            "id": str(track["track_id"]), "label": "person", "source": "semi-auto",
        })
        for b in track["boxes"]:
            _emit(el, b["frame"], b["box"], b["attributes"], outside=False)
        last = track["boxes"][-1]
        if last["frame"] < stop_frame:
            _emit(el, last["frame"] + 1, last["box"], last["attributes"], outside=True)

    return minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
```

- [ ] **Step 4: Verificar que pasa.**

- [ ] **Step 5: Verificación cruzada de contrato (manual, un comando):**
  generar un XML con el writer y parsearlo con el parser del repo datasets:

```bash
cd /home/simonll4/projects && python3 - <<'EOF'
import sys
sys.path.insert(0, "e-ovrt_media-plane/src")
sys.path.insert(0, "e-ovrt_datasets/datasets/scripts")
from eovrt_media.tools.videogt import build_cvat_xml
from videogt.cvat_xml import parse_cvat_video_xml, attribute_states
import tempfile, pathlib
xml = build_cvat_xml([{"track_id": 0, "boxes": [
    {"frame": 0, "box": (1.0, 2.0, 3.0, 4.0), "attributes": {"has_helmet": True, "has_vest": True}},
    {"frame": 10, "box": (1.0, 2.0, 3.0, 4.0), "attributes": {"has_helmet": False, "has_vest": True}},
]}], stop_frame=20, width=100, height=100, task_name="x")
p = pathlib.Path(tempfile.mkdtemp()) / "a.xml"; p.write_text(xml)
doc = parse_cvat_video_xml(p)
states = attribute_states(doc["tracks"][0], "has_helmet", 20)
assert states[0] is True and states[10] is False and states[12] is None, states
print("✓ roundtrip writer→parser OK (cierre outside en frame 11)")
EOF
```

- [ ] **Step 6: Checkpoint** — `make test` + `make lint` en verde.

---

### Task 10: media-plane — orquestación y CLI (`preannotate_video.py`)

**Files:**
- Create: `src/eovrt_media/tools/preannotate_video.py`
- Modify: `pyproject.toml` (extra `dev`: agregar `"supervision"`)
- Test: `tests/tools/test_videogt.py` (agregar test de orquestación)

**Interfaces:**
- Consumes: Task 8/9 (`infer_attributes`, `smooth_bool`, `thin_track`,
  `build_cvat_xml`).
- Produces: `track_persons(frame_dets: list[dict], frame_rate: float) ->
  list[dict]` — entrada `{"frame": int, "persons": list[tuple[Box, float]],
  "helmets": list[Box], "vests": list[Box]}`, salida tracks
  `{"track_id", "boxes": [{"frame", "box", "attributes"}]}` (ByteTrack);
  `smooth_tracks(tracks: list[dict], window: int) -> list[dict]`;
  CLI `python -m eovrt_media.tools.preannotate_video <clip.mp4> --out F
  [--sample-fps 10] [--device cuda|cpu] [--person-threshold 0.25]
  [--ppe-threshold 0.35] [--preview]`.

- [ ] **Step 1: Agregar `supervision` al extra dev del pyproject**

```toml
dev = [
    "pytest",
    "ruff",
    "httpx",
    "supervision",
]
```

Run: `pip install -e ".[dev]"` (dentro del venv).

- [ ] **Step 2: Test de orquestación con detector sintético (falla)**

```python
from eovrt_media.tools.preannotate_video import smooth_tracks, track_persons


def _synthetic_frames():
    """Persona que se mueve en x; casco presente salvo parpadeo en frame 9."""
    frames = []
    for i in range(30):
        x = 100.0 + i * 2
        person = ((x, 50.0, x + 60.0, 250.0), 0.9)
        helmet = [] if i == 9 else [(x + 15, 55.0, x + 45, 85.0)]
        frames.append({"frame": i * 3, "persons": [person],
                       "helmets": helmet, "vests": []})
    return frames


def test_track_persons_da_un_track_estable():
    tracks = track_persons(_synthetic_frames(), frame_rate=10.0)
    assert len(tracks) == 1
    (track,) = tracks
    # ByteTrack puede tardar 1-2 frames en confirmar el track; exigir >= 28
    assert len(track["boxes"]) >= 28
    assert track["boxes"][0]["attributes"]["has_vest"] is False


def test_smooth_tracks_elimina_parpadeo_de_atributo():
    tracks = track_persons(_synthetic_frames(), frame_rate=10.0)
    smoothed = smooth_tracks(tracks, window=5)
    helmet_states = [b["attributes"]["has_helmet"] for b in smoothed[0]["boxes"]]
    assert all(helmet_states)  # el parpadeo del frame 9 desaparece
```

- [ ] **Step 3: Verificar fallo.**

- [ ] **Step 4: Implementación**

```python
# src/eovrt_media/tools/preannotate_video.py
"""Pre-anotación de video para el video-gt-lab (GT del clip bench, spec 43).

GDINO-base (más fuerte que el tiny evaluado — anti-circularidad) + ByteTrack
sobre las cajas de persona + inicialización de has_helmet/has_vest por
asociación espacial. Emite CVAT for video 1.1 listo para corrección humana.

Uso: python -m eovrt_media.tools.preannotate_video clip.mp4 --out clip.xml \
         [--sample-fps 10] [--device cuda] [--preview]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from eovrt_media.tools.videogt import (
    build_cvat_xml,
    infer_attributes,
    smooth_bool,
    thin_track,
)

console = Console()

MODEL_ID = "IDEA-Research/grounding-dino-base"
PROMPT = "person. helmet. safety vest."


def track_persons(frame_dets: list[dict], frame_rate: float) -> list[dict]:
    """ByteTrack sobre cajas de persona; atributos por asociación espacial."""
    import numpy as np
    import supervision as sv

    tracker = sv.ByteTrack(frame_rate=frame_rate)
    tracks: dict[int, list[dict]] = {}
    for fd in frame_dets:
        persons = fd["persons"]
        detections = sv.Detections(
            xyxy=np.array([b for b, _ in persons], dtype=float).reshape(-1, 4),
            confidence=np.array([s for _, s in persons], dtype=float),
            class_id=np.zeros(len(persons), dtype=int),
        )
        detections = tracker.update_with_detections(detections)
        for box, tid in zip(detections.xyxy, detections.tracker_id):
            box = tuple(float(v) for v in box)
            tracks.setdefault(int(tid), []).append({
                "frame": fd["frame"],
                "box": box,
                "attributes": infer_attributes(box, fd["helmets"], fd["vests"]),
            })
    return [{"track_id": tid, "boxes": boxes} for tid, boxes in sorted(tracks.items())]


def smooth_tracks(tracks: list[dict], window: int = 11) -> list[dict]:
    """Suaviza los atributos de cada track (voto por mayoría, ventana centrada)."""
    out = []
    for track in tracks:
        boxes = [dict(b) for b in track["boxes"]]
        for attr in ("has_helmet", "has_vest"):
            smoothed = smooth_bool([b["attributes"][attr] for b in boxes], window)
            for b, value in zip(boxes, smoothed):
                b["attributes"] = {**b["attributes"], attr: value}
        out.append({"track_id": track["track_id"], "boxes": boxes})
    return out


def _make_detector(device: str, person_threshold: float, ppe_threshold: float):
    """Detector GDINO-base → {'persons': [(Box, score)], 'helmets': [...], 'vests': [...]}.

    NOTA: replicar la invocación de processor/post_process del adaptador
    existente (models/grounding_dino_adapter.py) — la API de transformers
    varía entre versiones y el adaptador ya está alineado con la instalada.
    """
    import torch
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(MODEL_ID).to(device)
    model.eval()

    def detect(image_pil):
        inputs = processor(images=image_pil, text=PROMPT, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        (result,) = processor.post_process_grounded_object_detection(
            outputs, inputs.input_ids,
            threshold=min(person_threshold, ppe_threshold),
            text_threshold=0.25,
            target_sizes=[image_pil.size[::-1]],
        )
        persons, helmets, vests = [], [], []
        for box, score, label in zip(result["boxes"], result["scores"], result["labels"]):
            box = tuple(float(v) for v in box.tolist())
            score = float(score)
            if "person" in label and score >= person_threshold:
                persons.append((box, score))
            elif "helmet" in label and score >= ppe_threshold:
                helmets.append(box)
            elif "vest" in label and score >= ppe_threshold:
                vests.append(box)
        return {"persons": persons, "helmets": helmets, "vests": vests}

    return detect


def _write_preview(video_path: Path, tracks: list[dict], out_path: Path) -> None:
    """MP4 con overlay (caja + id + estado EPP) para inspección pre-CVAT."""
    import cv2

    by_frame: dict[int, list[tuple[int, dict]]] = {}
    for track in tracks:
        for b in track["boxes"]:
            by_frame.setdefault(b["frame"], []).append((track["track_id"], b))
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (width, height))
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        for tid, b in by_frame.get(frame_idx, []):
            x1, y1, x2, y2 = (int(v) for v in b["box"])
            ok_ppe = b["attributes"]["has_helmet"] and b["attributes"]["has_vest"]
            color = (0, 200, 0) if ok_ppe else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            text = (f"#{tid} casco:{'si' if b['attributes']['has_helmet'] else 'NO'} "
                    f"chaleco:{'si' if b['attributes']['has_vest'] else 'NO'}")
            cv2.putText(frame, text, (x1, max(15, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        writer.write(frame)
        frame_idx += 1
    cap.release()
    writer.release()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="clip CFR preparado (etapa 0)")
    parser.add_argument("--out", type=Path, required=True, help="XML de salida")
    parser.add_argument("--sample-fps", type=float, default=10.0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--person-threshold", type=float, default=0.25)
    parser.add_argument("--ppe-threshold", type=float, default=0.35)
    parser.add_argument("--smooth-window", type=int, default=11)
    parser.add_argument("--thin-eps-px", type=float, default=10.0)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)

    import cv2
    from PIL import Image

    cap = cv2.VideoCapture(str(args.video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, round(fps / args.sample_fps))
    console.print(f"[cyan]{args.video.name}[/cyan]: {width}x{height} @ {fps:.0f} fps, "
                  f"{n_frames} frames — muestreo cada {step} frames")

    detect = _make_detector(args.device, args.person_threshold, args.ppe_threshold)
    frame_dets = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % step == 0:
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frame_dets.append({"frame": frame_idx, **detect(image)})
        frame_idx += 1
    cap.release()

    tracks = track_persons(frame_dets, frame_rate=args.sample_fps)
    tracks = smooth_tracks(tracks, window=args.smooth_window)
    if args.preview:
        preview_path = args.out.with_suffix(".preview.mp4")
        _write_preview(args.video, tracks, preview_path)
        console.print(f"[dim]preview:[/dim] {preview_path}")
    thinned = [{"track_id": t["track_id"], "boxes": thin_track(t["boxes"], args.thin_eps_px)}
               for t in tracks]

    xml = build_cvat_xml(thinned, stop_frame=n_frames - 1, width=width,
                         height=height, task_name=args.video.stem)
    args.out.write_text(xml)
    total_kf = sum(len(t["boxes"]) for t in thinned)
    console.print(f"[green]✓[/green] {args.out} — {len(thinned)} track(s), "
                  f"{total_kf} keyframes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Verificar tests** — `python -m pytest tests/tools/test_videogt.py -q`
  (los tests de orquestación usan detector sintético, sin GPU ni modelo).

- [ ] **Step 6: Checkpoint** — `make test` + `make lint` en verde;
  `pip install -e ".[dev]"` sin conflictos.

---

### Task 11: Smoke end-to-end sobre `recorte-1` (spec §7)

**Files:** ninguno nuevo — ejecución guiada + checklist del spec.

**Interfaces:** consume todo lo anterior.

- [ ] **Step 1: Pre-anotación real (GPU)**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && source .venv/bin/activate
python -m eovrt_media.tools.preannotate_video \
    ../e-ovrt_datasets/datasets-videos/clips/lab_recorte1.mp4 \
    --out ../e-ovrt_datasets/datasets-videos/preann/lab_recorte1.xml \
    --preview
```

Verificar: tracks de persona presentes; keyframes en el orden de decenas por
track (no cientos); inspeccionar `lab_recorte1.preview.mp4` a ojo (cajas
siguen a las personas, estados de EPP plausibles).

- [ ] **Step 2: Roundtrip CVAT (manual, en la PC con CVAT)**

Crear proyecto con `cvat_labels.json` → task con `lab_recorte1.mp4` → importar
`lab_recorte1.xml` → **exportar SIN editar** → derivar de ambos XML (importado
y exportado) y verificar que el GT resultante es idéntico (criterio de
roundtrip del spec §7). Después: corregir de verdad siguiendo el protocolo §5
del spec y exportar a `datasets-videos/corrected/lab_recorte1.xml`.

- [ ] **Step 3: Derivar y validar**

```bash
cd /home/simonll4/projects/e-ovrt_datasets
# escribir a mano datasets-videos/lab_recorte1.clip.yaml (block A, scenario y
# level según lo que muestre el video; ver spec §4.2)
python3 datasets/scripts/videogt/derive_clip_gt.py \
    --xml datasets-videos/corrected/lab_recorte1.xml \
    --clip-yaml datasets-videos/lab_recorte1.clip.yaml \
    --info datasets-videos/clips/lab_recorte1.info.json \
    --out datasets-videos/gt/lab_recorte1.json
# revisar el timeline impreso CONTRA EL VIDEO (regla de oro)
python3 datasets/scripts/bench/validate_clip_gt.py --gt-dir datasets-videos/gt
```

Expected: timeline coherente con lo que se ve; validador `✓ 0 error(es)`.

- [ ] **Step 4: Ensayo de doble anotación**

Segunda corrección independiente del mismo XML de pre-anotación (o el mismo
anotador en otra sesión, para el ensayo) → derivar →
`python3 datasets/scripts/videogt/compare_annotations.py --a gt/a.json --b gt/b.json`
→ kappa y |Δstart|/|Δend| emitidos.

- [ ] **Step 5: Cierre**

Marcar la checklist §7 del spec; ambas suites (`datasets`, `media-plane`) en
verde; avisar al usuario que el laboratorio está operativo y que el paso
siguiente es la ejecución del spec 43 (grabación A+C, banco real). **Sin
commits** salvo pedido explícito.
