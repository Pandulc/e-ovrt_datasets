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
