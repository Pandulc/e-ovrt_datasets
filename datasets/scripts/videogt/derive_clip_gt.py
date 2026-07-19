"""Derivación determinística de clip_gt.v2 desde CVAT XML corregido.

Regla de oro (spec 43 §3.3): el GT sale del video corregido por el humano;
este script solo hace la aritmética. Las reglas viven en el spec del
laboratorio (docs/_archive/superpowers/specs/2026-07-11-video-gt-lab-design.md §3.3).

Identidad de los episodios (contrato del evaluador, control-plane
`evaluation/temporal.py`): TODO episodio lleva `source_id` — convención
`source_id = clip_id`, con override opcional vía `source_id` en clip.yaml —
porque el matching de escena del evaluador es `alert.source_id ==
episode.source_id` (la corrida del bench configura su fuente con el
clip_id). Los episodios `level: subject` llevan además `subject_key` =
`subject_label`: una clave LOCAL a este clip, derivada de los tracks de
CVAT (`persona_A`, `persona_B`, …). Esa clave NO mapea a las claves
`{pattern}:{source}:{track}` que usa el motor de alertas en vivo — el
matching automático por sujeto individual no es posible con este GT. Los
clips P7 con `level: subject` sirven para comparación cualitativa G0/G1;
para métricas (recall/precision) esos episodios se derivan a nivel scene.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from videogt.cvat_xml import attribute_states  # noqa: E402

CONDITIONS = {"CR-01": "has_helmet", "CR-02": "has_vest"}
# Alineado con el pattern set OFICIAL del motor (control-plane
# configs/patterns/cr01_cr02_v2.yaml, que cita la Tabla 24/D.4 del informe:
# CR-01 high confirm_after_ms=4000, CR-02 medium confirm_after_ms=7000).
# Si este default y el motor divergen, los intervalos entre ambos umbrales se
# clasifican como episodios que el motor nunca confirma -> falsos `missed` y
# recall deprimido. Ante la duda, pasar --pattern-set explicito.
DEFAULT_PATTERN_SET_MS = {"CR-01": 4000, "CR-02": 7000}
# A1 — gate de dimensionamiento (doc 57 §6.5/§6.7, Tabla 35/D.4). Para que un
# episodio sea evaluable sin censura temporal el clip debe extenderse hasta el
# borde superior de `t_alert-system` de su patrón MÁS resolve MÁS una cola. Esto
# NO es la persistencia (confirm_after_ms del pattern set) — es el techo de la
# métrica de latencia por severidad. Si el clip queda por debajo, t_alert-system
# y recall de ese episodio no son concluyentes (los declara `metric_censored` el
# evaluador). El aviso va en provenance, NO bloquea la derivación.
DIMENSIONING_MS = {
    "CR-01": {"t_alert_upper_ms": 10000, "resolve_ms": 2000},   # PR-01 alto
    "CR-02": {"t_alert_upper_ms": 20000, "resolve_ms": 3000},   # PR-02 medio
}
MIN_ONSET_MS = 2000   # el onset del primer episodio nunca en t≈0 (pre-roll)
DIMENSIONING_TAIL_MS = 2000   # cola para observar el cierre por resolve
START_END_TOLERANCE_MS = 500
TOOL_NAME = "video-gt-lab/derive_clip_gt"
SIZE_MISMATCH_TOLERANCE_FRAMES = 1
REQUIRED_CLIP_META_FIELDS = ["clip_id", "block", "scenario"]
VALID_LEVELS = {"scene", "subject"}


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
    """Separa episodios (duración ≥ persistencia mínima) de eventos sub-umbral.

    Los sub-umbral propagan ``track_id``/``subject_label`` cuando el intervalo
    de entrada los trae (C1): un sub-umbral de escena sigue identificando a QUÉ
    track pertenece (a ese track no lo hubiese alertado el motor 1:1), y un
    sub-umbral de nivel subject conserva el ``subject_label`` del sujeto.
    """
    episodes, sub_events = [], []
    for iv in intervals:
        duration = iv["end_ms"] - iv["start_ms"]
        minimum = pattern_set_ms[iv["condition_id"]]
        if duration >= minimum:
            episodes.append(dict(iv))
        else:
            sub_event = {
                "condition_id": iv["condition_id"],
                "start_ms": iv["start_ms"],
                "end_ms": iv["end_ms"],
                "reason": (
                    f"transitorio < persistencia mínima "
                    f"({duration} ms < {minimum} ms) — NO debe alertar"
                ),
            }
            if "track_id" in iv:
                sub_event["track_id"] = iv["track_id"]
            if "subject_label" in iv:
                sub_event["subject_label"] = iv["subject_label"]
            sub_events.append(sub_event)
    return episodes, sub_events


def dimensioning_warnings(gt: dict) -> list[str]:
    """Avisos de dimensionamiento del clip (A1, doc 57 §6.5/§6.7).

    Puramente aritmético sobre los tiempos del GT — NO bloquea nada. Un clip
    negativo (sin episodios) no tiene métrica temporal que censurar, así que no
    genera avisos. Para cada episodio se exige que la duración del clip alcance
    el borde superior de `t_alert-system` de su condición + resolve + cola; si
    no, ese episodio queda censurado para t_alert-system/recall (el evaluador lo
    marca `metric_censored`). Además, el onset del primer episodio no debe caer
    antes de `MIN_ONSET_MS` (sin pre-roll el TTFD colapsa a 0 como artefacto de
    recorte, como en `video16_clip10`).
    """
    warnings = []
    episodes = gt.get("episodes", [])
    if not episodes:
        return warnings
    # `duration_ms` es opcional en el schema v2: sin ella no se puede computar el
    # floor de censura, pero el chequeo de onset (que no la usa) sigue. La función
    # es un warning, nunca rompe — de ahí el `.get()` (espeja el guard de
    # `episodes`/`condition_id`).
    duration = gt.get("duration_ms")
    first_start = min(ep["start_ms"] for ep in episodes)
    if first_start < MIN_ONSET_MS:
        warnings.append(
            f"onset del primer episodio en {first_start} ms (< {MIN_ONSET_MS} ms): "
            "sin pre-roll el TTFD colapsa a 0 como artefacto de recorte — "
            "re-ventanear el corte para que el onset caiga en t≈3–4 s (doc 57 §6.5)"
        )
    if duration is None:
        return warnings
    for ep in episodes:
        dim = DIMENSIONING_MS.get(ep["condition_id"])
        if dim is None:
            continue
        floor = ep["start_ms"] + dim["t_alert_upper_ms"] + dim["resolve_ms"] + DIMENSIONING_TAIL_MS
        if duration < floor:
            warnings.append(
                f"{ep['id']} ({ep['condition_id']}): duration_ms {duration} < {floor} ms "
                f"(start {ep['start_ms']} + t_alert_upper {dim['t_alert_upper_ms']} + "
                f"resolve {dim['resolve_ms']} + cola {DIMENSIONING_TAIL_MS}): "
                "t_alert-system/recall de este episodio quedan censurados (doc 57 §6.7)"
            )
    return warnings


def _column_label(i: int) -> str:
    """Índice 0-based → etiqueta estilo columna de hoja de cálculo.

    A, B, …, Z, AA, AB, …, AZ, BA, … Nunca se sale del alfabeto: a
    diferencia de `chr(65 + i)`, que produce basura ilegible/ambigua a
    partir de i=26 (p.ej. `\\``, `_`, minúsculas que colisionan con una
    hipotética mayúscula), este esquema crece agregando dígitos como en
    las columnas de una planilla de cálculo.
    """
    label = ""
    i += 1  # 1-based para el algoritmo de conversión a base-26 sin cero
    while i > 0:
        i, rem = divmod(i - 1, 26)
        label = chr(65 + rem) + label
    return label


def subject_labels(tracks: list[dict]) -> dict[int, str]:
    """track_id → persona_A, persona_B, …, persona_Z, persona_AA, …

    Orden por track_id ascendente (spec 43 §4.3). Las etiquetas usan
    `_column_label` para no salirse nunca del rango A-Z aunque haya más
    de 26 tracks.
    """
    ordered = sorted(t["track_id"] for t in tracks)
    return {tid: f"persona_{_column_label(i)}" for i, tid in enumerate(ordered)}


def assemble_clip_gt(clip_meta: dict, clip_info: dict,
                     episodes: list[dict], sub_events: list[dict]) -> dict:
    """Ensambla el JSON clip_gt.v2 (schema del spec 43 §4).

    FIX 1 (auditoría 2026-07-11, contrato con el evaluador del control-plane
    — `evaluation/temporal.py`, ClipEpisodeV2): TODO episodio lleva
    `source_id`, con convención `source_id = clip_id` y override opcional
    vía el campo `source_id` de clip.yaml — es lo que el evaluador matchea
    contra `alert.source_id` para episodios de escena. Los episodios
    `level: subject` llevan ADEMÁS `subject_key` = `subject_label`: una
    clave LOCAL a este clip derivada de los tracks de CVAT (`persona_A`,
    `persona_B`, …) que NO mapea a las claves `{pattern}:{source}:{track}`
    del motor de alertas en vivo — el matching automático por sujeto
    individual no es posible con este GT. Los clips P7 con level subject son
    para comparación cualitativa G0/G1; para métricas se derivan a nivel
    scene.
    """
    level = clip_meta.get("level", "scene")
    duration_ms = clip_info["duration_ms"]
    source_id = clip_meta.get("source_id") or clip_meta["clip_id"]
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
            "source_id": source_id,
            "start_ms": ep["start_ms"],
            "end_ms": ep["end_ms"],
            "subjects_in_evidence": ep["subjects_in_evidence"],
            "notes": notes,
        }
        if level == "subject":
            entry["subject_label"] = ep["subject_label"]
            entry["subject_key"] = ep["subject_label"]
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


def _parse_pattern_set(text: str) -> dict:
    """'CR-01=4000,CR-02=7000' → {'CR-01': 4000, 'CR-02': 7000}.

    FIX 7 (auditoría 2026-07-11): un valor no entero (p.ej. 'CR-01=abc')
    antes reventaba con el ValueError crudo de `int()`. Acá se relanza con
    un mensaje que dice qué clave y qué valor fallaron.
    """
    out = dict(DEFAULT_PATTERN_SET_MS)
    for part in filter(None, (p.strip() for p in text.split(","))):
        key, _, value = part.partition("=")
        key = key.strip()
        try:
            out[key] = int(value)
        except ValueError:
            raise ValueError(
                f"--pattern-set: valor no entero para {key!r} ({value!r}); "
                "formato esperado 'CR-01=4000,CR-02=7000'"
            ) from None
    return out


def _fmt_ms(ms: int) -> str:
    return f"{ms // 60000:02d}:{(ms % 60000) / 1000:06.3f}"


def load_clip_meta(clip_yaml_path) -> dict:
    """Carga y valida `clip.yaml` (spec 44 §4.2).

    FIX 4 (auditoría 2026-07-11): antes, un clip.yaml incompleto explotaba
    más adelante con un KeyError críptico (p.ej. al leer `clip_meta["clip_id"]`
    en `assemble_clip_gt`); acá se valida temprano y se listan TODOS los
    campos faltantes de una vez.

    FIX 3: `level` (opcional, default "scene") debe ser exactamente "scene" o
    "subject". Antes, cualquier valor que no fuera la cadena literal
    "subject" (un typo como "Subject" o " scene" con espacio) caía
    silenciosamente al branch "scene" en `derive()`, fusionando sujetos que
    no debía fusionarse.
    """
    clip_meta = yaml.safe_load(Path(clip_yaml_path).read_text())
    if not isinstance(clip_meta, dict):
        raise ValueError(f"{clip_yaml_path}: clip.yaml vacío o mal formado (se esperaba un mapeo)")

    missing = [f for f in REQUIRED_CLIP_META_FIELDS if f not in clip_meta]
    if missing:
        raise ValueError(
            f"{clip_yaml_path}: faltan campos requeridos en clip.yaml: "
            f"{', '.join(missing)}"
        )

    level = clip_meta.get("level", "scene")
    if level not in VALID_LEVELS:
        raise ValueError(
            f"{clip_yaml_path}: level {level!r} inválido — debe ser uno de "
            f"{sorted(VALID_LEVELS)} (revisá mayúsculas y espacios; un typo "
            "acá fusionaría sujetos que no debía)"
        )

    for key in ("recording", "annotation"):
        if key in clip_meta and not isinstance(clip_meta[key], dict):
            raise ValueError(
                f"{clip_yaml_path}: '{key}' debe ser un mapeo (dict) en "
                f"clip.yaml, recibido {type(clip_meta[key]).__name__}"
            )

    return clip_meta


def derive(xml_path, clip_yaml_path, info_json_path, pattern_set_ms: dict,
           allow_empty: bool = False) -> dict:
    """Pipeline completo: XML corregido + clip.yaml + info.json → clip_gt.v2."""
    from videogt.cvat_xml import parse_cvat_video_xml

    doc = parse_cvat_video_xml(xml_path)
    clip_meta = load_clip_meta(clip_yaml_path)
    clip_info = json.loads(Path(info_json_path).read_text())
    fps = clip_info["fps"]
    n_frames = clip_info["n_frames"]
    end_frame = n_frames - 1

    # I2: si el <size> del XML no corresponde al n_frames del clip preparado,
    # truncar en silencio puede recortar episodios reales. Tolerancia de 1
    # frame por el desfase habitual entre cv2 y ffprobe.
    if doc["stop_frame"] is not None:
        xml_frames = doc["stop_frame"] + 1
        if abs(xml_frames - n_frames) > SIZE_MISMATCH_TOLERANCE_FRAMES:
            raise ValueError(
                f"el <size> del XML ({xml_frames} frames, {xml_path}) no "
                f"coincide con n_frames de {info_json_path} ({n_frames} "
                f"frames) — diferencia de {abs(xml_frames - n_frames)} frames, "
                f"supera la tolerancia de {SIZE_MISMATCH_TOLERANCE_FRAMES}. El "
                "clip anotado en CVAT no corresponde al clip preparado por "
                "prepare_clip.sh (¿tarea creada sobre otro video, o video sin "
                "pasar por la etapa 0?). Volvé a exportar el XML sobre el "
                "clip correcto."
            )
        end_frame = min(end_frame, doc["stop_frame"])

    # C2: cero tracks 'person' no debe fabricar un negativo silencioso — un
    # export mal formado ("CVAT for images", label "Person" con mayúscula,
    # etc.) produciría episodes=0/negative=true, y toda violación real del
    # clip entraría al banco como FP.
    persons = [t for t in doc["tracks"] if t["label"] == "person"]
    if not persons and not allow_empty:
        found_labels = sorted({t["label"] for t in doc["tracks"]})
        found_desc = ", ".join(repr(label) for label in found_labels) or "ninguno"
        raise ValueError(
            f"no se encontró ningún track con label exactamente 'person' en "
            f"{xml_path} (labels encontrados: {found_desc}). Revisá el "
            "formato de export en CVAT (debe ser 'CVAT for video 1.1', no "
            "'CVAT for images 1.1') y la capitalización exacta del label "
            "('person', no 'Person' ni variantes). Si este clip es un "
            "negativo intencional (sin personas en cuadro), volvé a correr "
            "con --allow-empty (CLI) / allow_empty=True (función)."
        )

    raw = [iv for t in persons for iv in track_condition_intervals(t, end_frame, fps)]

    level = clip_meta.get("level", "scene")
    if level == "subject":
        labels = subject_labels(persons)
        intervals = [
            {**iv, "subjects_in_evidence": 1, "subject_label": labels[iv["track_id"]]}
            for iv in raw
        ]
        episodes, sub_events = classify_intervals(intervals, pattern_set_ms)
    else:
        # C1: umbralar POR TRACK primero, fusionar los sobrevivientes después.
        # Fusionar antes de aplicar la persistencia mínima fabrica episodios
        # de escena que ningún sujeto individual sostuvo — el motor de
        # alertas del control-plane es 1:1 por sujeto y no alertaría ninguno
        # de los tracks sub-umbral, así que ese episodio fantasma se contaría
        # como "missed" y subestimaría el recall de CR-01/CR-02.
        per_track_episodes, sub_events = classify_intervals(raw, pattern_set_ms)
        episodes = merge_scene_intervals(per_track_episodes)

    gt = assemble_clip_gt(clip_meta, clip_info, episodes, sub_events)
    # I3: procedencia para determinismo auditable.
    gt["provenance"] = {
        "xml_sha256": hashlib.sha256(Path(xml_path).read_bytes()).hexdigest(),
        "pattern_set_ms": pattern_set_ms,
        "tool": TOOL_NAME,
        # A1: gate de dimensionamiento (doc 57 §6.5/§6.7). Auditoría, no bloquea.
        "dimensioning_warnings": dimensioning_warnings(gt),
    }
    return gt


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
    for w in gt.get("provenance", {}).get("dimensioning_warnings", []):
        print(f"  ⚠ DIMENSIONAMIENTO  {w}")
    print("Revisar contra el video antes de promover al banco.\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", required=True, help="CVAT XML corregido")
    parser.add_argument("--clip-yaml", required=True, help="metadata del clip (spec §4.2)")
    parser.add_argument("--info", required=True, help="<clip_id>.info.json de prepare_clip.sh")
    parser.add_argument("--out", required=True, help="salida clip_gt.v2 JSON")
    parser.add_argument("--pattern-set", default="", help="ej: CR-01=4000,CR-02=7000")
    parser.add_argument("--allow-empty", action="store_true",
                        help="permite GT negativo sin tracks 'person' (negativo intencional)")
    args = parser.parse_args(argv)

    try:
        pattern_set_ms = _parse_pattern_set(args.pattern_set)
    except ValueError as e:
        parser.error(str(e))  # imprime uso + mensaje a stderr y sale con código 2

    gt = derive(args.xml, args.clip_yaml, args.info, pattern_set_ms,
               allow_empty=args.allow_empty)
    Path(args.out).write_text(json.dumps(gt, indent=2, ensure_ascii=False) + "\n")
    _print_timeline(gt)
    print(f"GT escrito en {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
