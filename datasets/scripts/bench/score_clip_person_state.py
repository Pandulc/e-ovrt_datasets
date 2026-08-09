"""Nivel A (estado por persona) sobre CLIPS de video con GT humano de CVAT.

Hermano de `run_fase_d_nivel_a.py`, que puntua Nivel A sobre el bench de IMAGENES
(`bench_v3`). Este puntua lo mismo sobre clips, usando como GT las cajas + atributos
`has_helmet`/`has_vest` que el anotador corrigio frame a frame en CVAT.

POR QUE EXISTE: los clips de 12 s del piloto (doc 102) tienen todos sus episodios
CENSURADOS por el gate A1 — a Nivel B (alerta) no producen recall. Pero Nivel A
**no depende de la duracion del clip**: mide, por persona y por frame, si el sistema
determina bien su estado. Es exactamente la capa que el doc 103 §7 encontro como raiz
del problema del estrato B, y hasta ahora se media con un proxy ad-hoc
(`103-diagnostico-juzgabilidad.py`, centro-en-caja). Este script la mide con el
scorer OFICIAL y las MISMAS regiones del pattern set desplegado.

TRES DECISIONES METODOLOGICAS, todas explicitas en la salida:

1. `unknown` SE EXCLUYE, no se cuenta como cumplimiento. Si el anotador no pudo
   determinar el estado, esa persona-frame sale del denominador de esa condicion.
   Contarla como `True` inventaria cumplimiento; contarla como `False` inventaria
   violaciones. Es el mismo principio que `derive_clip_gt` defiende ("la
   incertidumbre nunca fabrica una violacion") y el que el runtime NO tiene
   (F-104.4). El conteo de exclusiones se reporta: en clips far-field es enorme y
   ESE es un resultado.

2. SUB-MUESTREO TEMPORAL. Frames contiguos son casi identicos; puntuar los 360
   frames infla `n` y falsea cualquier intervalo de confianza. Default: 1 de cada 15
   (2 Hz). El `n` reportado es de persona-frames efectivamente puntuados.

3. SIN BARRIDO DE UMBRALES. El runner de imagenes calibra en la mitad A y reporta en
   la B; con 4 clips no hay material para eso y barrer seria ajuste in-sample. Se
   puntua en el PUNTO DE OPERACION DESPLEGADO (los valores del pattern set
   `cr01_cr02_v2`), que es lo que la plataforma hace de verdad.

Uso:
    python3 datasets/scripts/bench/score_clip_person_state.py \\
        --clips video02_clip07,video15_clip01 \\
        --runs-map <json {clip_id: media_run_id}> \\
        --xml-dir <dir con <clip_id>.xml corregidos> \\
        --out <salida.json> [--stride 15]
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/

from bench.score_person_state import (  # noqa: E402
    add_counts,
    match_predictions_to_gt,
    predict_eind,
    prf1,
)
from videogt.cvat_xml import attribute_states, parse_cvat_video_xml  # noqa: E402

MEDIA_RUNS = Path(__file__).resolve().parents[3].parent / "e-ovrt_media-plane" / "runs"

# Regiones y umbrales del pattern set DESPLEGADO `cr01_cr02_v2`. Si esto diverge del
# YAML, el numero de Nivel A deja de predecir el de Nivel B.
CONDICIONES = {
    "CR-01": {
        "attribute": "has_helmet",
        "evidence_label": "helmet",
        "region": {"y_min_ratio": 0.0, "y_max_ratio": 0.45, "x_margin_ratio": 0.12},
    },
    "CR-02": {
        "attribute": "has_vest",
        "evidence_label": "vest",
        "region": {"y_min_ratio": 0.25, "y_max_ratio": 0.85, "x_margin_ratio": 0.08},
    },
}
PERSON_CONF = 0.35        # evidence.min_subject_confidence
EVIDENCE_CONF = 0.25      # evidence.min_absent_class_confidence


def _geometria_por_track(xml_path: Path) -> dict[int, dict[int, list[float]]]:
    """track_id -> {frame: [x1,y1,x2,y2]}, leido directo del XML.

    `videogt.cvat_xml` deliberadamente NO expone la geometria (a `derive_clip_gt` le
    alcanzan los atributos), y no se toca desde aca: es el corazon de la cadena de GT
    y no vale el riesgo de regresion por una necesidad de este scorer. El export
    "CVAT for video 1.1" emite una caja por frame ya interpolada, asi que no hay que
    interpolar nada; las `outside=1` se descartan.
    """
    root = ET.parse(str(xml_path)).getroot()
    geo: dict[int, dict[int, list[float]]] = {}
    for tr in root.findall("track"):
        if tr.get("label") != "person":
            continue
        tid = int(tr.get("id"))
        por_frame = {}
        for b in tr.findall("box"):
            if b.get("outside") == "1":
                continue
            por_frame[int(b.get("frame"))] = [
                float(b.get("xtl")), float(b.get("ytl")),
                float(b.get("xbr")), float(b.get("ybr")),
            ]
        geo[tid] = por_frame
    return geo


def gt_por_frame(xml_path: Path, n_frames: int) -> dict[int, list[dict]]:
    """frame -> [{person_bbox, has_helmet, has_vest}], desde el CVAT corregido.

    Geometria leida del XML; atributos via `attribute_states`, que materializa la
    semantica escalon de CVAT (un atributo mutable vale hasta el proximo keyframe).
    Los atributos van con su valor real, `None` incluido: el filtrado por condicion
    lo hace el llamador, para poder contar cuantas person-frames excluye cada una.
    """
    doc = parse_cvat_video_xml(xml_path)
    geo = _geometria_por_track(xml_path)
    por_frame: dict[int, list[dict]] = {}
    for t in doc["tracks"]:
        if t["label"] != "person":
            continue
        estados = {attr: attribute_states(t, attr, n_frames - 1)
                   for attr in ("has_helmet", "has_vest")}
        for f, bbox in geo.get(t["track_id"], {}).items():
            if f >= n_frames:
                continue
            por_frame.setdefault(f, []).append({
                "person_bbox": bbox,
                "has_helmet": estados["has_helmet"][f],
                "has_vest": estados["has_vest"][f],
                "track_id": t["track_id"],
            })
    return por_frame


def detecciones_por_frame(run_dir: Path) -> dict[int, list[dict]]:
    por_frame: dict[int, list[dict]] = {}
    with (run_dir / "detections.jsonl").open() as fh:
        for line in fh:
            if not line.strip():
                continue
            ev = json.loads(line)
            f = ev["source"].get("frame_index")
            if f is None:
                continue
            por_frame.setdefault(int(f), []).extend(ev.get("detections") or [])
    return por_frame


def puntuar_clip(clip_id, xml_path, run_dir, n_frames, stride):
    gt = gt_por_frame(xml_path, n_frames)
    det = detecciones_por_frame(run_dir)
    frames = [f for f in sorted(gt) if f % stride == 0]
    salida = {"clip_id": clip_id, "frames_puntuados": len(frames), "stride": stride,
              "por_condicion": {}}
    for cond, cfg in CONDICIONES.items():
        attr = cfg["attribute"]
        counts = {"tp": 0, "fp": 0, "fn": 0, "n_gt": 0, "n_gt_positive": 0}
        excluidas = incluidas = 0
        for f in frames:
            registros = gt.get(f, [])
            conocidas = [r for r in registros if r.get(attr) is not None]
            excluidas += len(registros) - len(conocidas)
            incluidas += len(conocidas)
            if not conocidas:
                continue
            preds = predict_eind(det.get(f, []), cfg["evidence_label"], cfg["region"],
                                 PERSON_CONF, EVIDENCE_CONF)
            counts = add_counts(counts, match_predictions_to_gt(conocidas, preds, attr))
        m = prf1(counts)
        total = incluidas + excluidas
        salida["por_condicion"][cond] = {
            **counts, **m,
            "person_frames_evaluadas": incluidas,
            "person_frames_excluidas_unknown": excluidas,
            "ratio_unknown": round(excluidas / total, 4) if total else None,
        }
    return salida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--runs-map", required=True, help="JSON {clip_id: media_run_id}")
    ap.add_argument("--xml-dir", required=True)
    ap.add_argument("--info-dir", required=True, help="dir con <clip_id>.info.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stride", type=int, default=15)
    a = ap.parse_args(argv)

    runs = json.loads(Path(a.runs_map).read_text()) if Path(a.runs_map).exists() \
        else json.loads(a.runs_map)
    clips = [c.strip() for c in a.clips.split(",") if c.strip()]

    resultados, agregado = [], {}
    for cid in clips:
        info = json.loads((Path(a.info_dir) / f"{cid}.info.json").read_text())
        r = puntuar_clip(cid, Path(a.xml_dir) / f"{cid}.xml",
                         MEDIA_RUNS / runs[cid], info["n_frames"], a.stride)
        resultados.append(r)
        for cond, d in r["por_condicion"].items():
            agregado.setdefault(cond, {"tp": 0, "fp": 0, "fn": 0, "n_gt": 0,
                                       "n_gt_positive": 0,
                                       "person_frames_evaluadas": 0,
                                       "person_frames_excluidas_unknown": 0})
            for k in agregado[cond]:
                agregado[cond][k] += d[k]

    for cond, d in agregado.items():
        d.update(prf1(d))
        tot = d["person_frames_evaluadas"] + d["person_frames_excluidas_unknown"]
        d["ratio_unknown"] = round(d["person_frames_excluidas_unknown"] / tot, 4) if tot else None

    out = {
        "schema_version": "clip_person_state.v1",
        "operating_point": {"person_conf": PERSON_CONF, "evidence_conf": EVIDENCE_CONF,
                            "pattern_set": "cr01_cr02_v2 (desplegado)",
                            "sin_barrido": "puntuado en el punto de operacion, no calibrado"},
        "stride": a.stride,
        "unknown_policy": "person-frames con atributo unknown EXCLUIDAS del denominador",
        "por_clip": resultados,
        "agregado": agregado,
    }
    Path(a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    print(f"punto de operacion: person>={PERSON_CONF} evidencia>={EVIDENCE_CONF} "
          f"| stride={a.stride} | unknown EXCLUIDO\n")
    print(f"{'clip':>16} {'cond':>6} {'n eval':>7} {'unk %':>6} {'viol':>5} "
          f"{'TP':>4} {'FP':>4} {'FN':>4} {'P':>6} {'R':>6} {'F1':>6}")
    for r in resultados:
        for cond, d in r["por_condicion"].items():
            def f(x):
                return "  —  " if x is None else f"{x:.3f}"
            print(f"{r['clip_id']:>16} {cond:>6} {d['person_frames_evaluadas']:>7} "
                  f"{100*(d['ratio_unknown'] or 0):>5.1f}% {d['n_gt_positive']:>5} "
                  f"{d['tp']:>4} {d['fp']:>4} {d['fn']:>4} "
                  f"{f(d['precision'])} {f(d['recall'])} {f(d['f1'])}")
    print()
    for cond, d in agregado.items():
        def f(x):
            return "  —  " if x is None else f"{x:.3f}"
        print(f"{'AGREGADO':>16} {cond:>6} {d['person_frames_evaluadas']:>7} "
              f"{100*(d['ratio_unknown'] or 0):>5.1f}% {d['n_gt_positive']:>5} "
              f"{d['tp']:>4} {d['fp']:>4} {d['fn']:>4} "
              f"{f(d['precision'])} {f(d['recall'])} {f(d['f1'])}")
    print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
