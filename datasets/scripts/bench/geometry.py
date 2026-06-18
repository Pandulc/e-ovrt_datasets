"""Geometría pura para matching detección<->GT (spec §6.2)."""

def center_in_bbox(inner: list[float], outer: list[float]) -> bool:
    """True si el centro de inner cae dentro de outer. Más robusto que IoU cuando
    los bboxes tienen áreas muy distintas (ej: bare_head vs head_region de persona)."""
    cx = (inner[0] + inner[2]) / 2
    cy = (inner[1] + inner[3]) / 2
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]

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
