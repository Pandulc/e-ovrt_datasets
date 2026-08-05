"""Fusion dual-run de dos corridas de deteccion, para E-HYB a Nivel B (doc 12 §4.1).

El pre-registro prohibe el pase unico de vocabulario union: en GDINO el vocabulario
es parte de la inferencia, asi que un caption con las 5 clases daria señales
DISTINTAS de las de T1/D1 y la comparacion dejaria de ser de variable unica. La
fusion se hace sobre las corridas YA HECHAS — **E-HYB a Nivel B no necesita GPU**.

Que el problema es real esta medido: `person` con la MISMA frase da distinta cantidad
de cajas segun el resto del caption (729 vs 731 en a_p1_c09; 1095 vs 1317 en
a_p2_c01).

Regla de fusion:
  - Del stream E-IND entra TODO -> `spatial_absence` ve exactamente lo de T1 y su
    evidencia es bit a bit la misma.
  - Del stream E-DIR entran SOLO las clases de evidencia directa. Sus `person` se
    descartan: dos cajas por persona duplicarian sujetos y romperian tanto
    `subjects_in_evidence` como la equivalencia con T1.

**Desviacion declarada:** el gating por persona de `direct_evidence` (doc 12 §4.2)
usa entonces las personas del stream E-IND, no las del E-DIR con las que se gatearon
en D1. Los HITS directos son bit a bit los de D1; lo que cambia es contra que sujetos
se gatean. Es coherente con §4.3 (E-IND es la señal primaria, y en el sistema fusionado
hay una sola fuente de sujetos), y el efecto se mide con `--medir-gating` en vez de
suponerse.
"""
import argparse
import json
from pathlib import Path


def merge_event(eind: dict, edir: dict, direct_classes: tuple[str, ...]) -> dict:
    """Fusiona dos eventos del MISMO frame en uno."""
    detections = list(eind.get("detections") or [])
    for det in edir.get("detections") or []:
        if det.get("label") not in direct_classes:
            continue
        copia = dict(det)
        # Ambas corridas numeran det_000001...: sin namespace se pisan en los sinks.
        if copia.get("detection_id"):
            copia["detection_id"] = f"edir_{copia['detection_id']}"
        detections.append(copia)

    fusionado = dict(eind)
    fusionado["detections"] = detections
    fusionado["prompts"] = {"prompt_set_id": "hyb_or_dual_run"}
    fusionado["fusion"] = {
        "eind_run_id": eind.get("run_id"),
        "edir_run_id": edir.get("run_id"),
    }
    return fusionado


def _load_by_frame(path: Path) -> dict[int, dict]:
    por_frame: dict[int, dict] = {}
    with Path(path).open() as fh:
        for line in fh:
            if not line.strip():
                continue
            ev = json.loads(line)
            por_frame[ev["source"]["frame_index"]] = ev
    return por_frame


def merge_detection_streams(
    eind_path: Path,
    edir_path: Path,
    out_path: Path,
    direct_classes: tuple[str, ...],
) -> dict:
    """Fusiona dos `detections.jsonl` frame a frame. Falla fuerte ante desalineacion.

    Alinear a ciegas cruzaria evidencia de frames (o de clips) distintos EN SILENCIO
    — la misma familia de trampa que el mtime del doc 82 y el export de CVAT.
    """
    a = _load_by_frame(eind_path)
    b = _load_by_frame(edir_path)

    solo_a, solo_b = set(a) - set(b), set(b) - set(a)
    if solo_a or solo_b:
        raise ValueError(
            f"streams desalineados: {len(solo_a)} frame(s) solo en E-IND y "
            f"{len(solo_b)} solo en E-DIR (ej: {sorted(solo_a | solo_b)[:5]})"
        )

    hits = 0
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(out_path).open("w") as fh:
        for frame in sorted(a):
            ea, eb = a[frame], b[frame]
            sa, sb = ea["source"], eb["source"]
            if sa.get("source_id") != sb.get("source_id"):
                raise ValueError(
                    f"source_id distinto en el frame {frame}: "
                    f"{sa.get('source_id')!r} vs {sb.get('source_id')!r} — "
                    "se estan fusionando dos clips distintos"
                )
            ta, tb = sa.get("timestamp_ms"), sb.get("timestamp_ms")
            if ta is not None and tb is not None and abs(ta - tb) > 1e-6:
                raise ValueError(
                    f"timestamp distinto en el frame {frame}: {ta} vs {tb}")
            fusionado = merge_event(ea, eb, direct_classes)
            hits += sum(1 for d in fusionado["detections"]
                        if d.get("label") in direct_classes)
            fh.write(json.dumps(fusionado, ensure_ascii=False) + "\n")

    return {"frames": len(a), "direct_hits": hits}


def medir_gating(
    eind_path: Path,
    edir_path: Path,
    direct_classes: tuple[str, ...],
    person_conf: float = 0.35,
    iou_thr: float = 0.5,
) -> dict:
    """Cuantifica la desviacion declarada: ¿cuantos hits directos que gateaban contra
    las personas de E-DIR siguen gateando contra las de E-IND?"""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from bench.geometry import iou

    a, b = _load_by_frame(eind_path), _load_by_frame(edir_path)
    gateaban = mantienen = 0
    for frame in sorted(set(a) & set(b)):
        p_eind = [d["bbox_xyxy"] for d in a[frame]["detections"]
                  if d["label"] == "person" and d["confidence"] >= person_conf]
        p_edir = [d["bbox_xyxy"] for d in b[frame]["detections"]
                  if d["label"] == "person" and d["confidence"] >= person_conf]
        for det in b[frame]["detections"]:
            if det.get("label") not in direct_classes:
                continue
            if any(iou(det["bbox_xyxy"], p) >= iou_thr for p in p_edir):
                gateaban += 1
                if any(iou(det["bbox_xyxy"], p) >= iou_thr for p in p_eind):
                    mantienen += 1
    return {
        "gated_en_edir": gateaban,
        "siguen_gateando_con_personas_eind": mantienen,
        "fraccion": (mantienen / gateaban) if gateaban else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--eind", required=True, type=Path, help="detections.jsonl de la corrida E-IND")
    ap.add_argument("--edir", required=True, type=Path, help="detections.jsonl de la corrida E-DIR")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--direct-classes", default="cr01_spec,cr02_obs")
    ap.add_argument("--medir-gating", action="store_true")
    a = ap.parse_args()

    clases = tuple(c.strip() for c in a.direct_classes.split(",") if c.strip())
    stats = merge_detection_streams(a.eind, a.edir, a.out, clases)
    print(f"{stats['frames']} frames, {stats['direct_hits']} hits directos -> {a.out}")
    if a.medir_gating:
        print("gating:", medir_gating(a.eind, a.edir, clases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
