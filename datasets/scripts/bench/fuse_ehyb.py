"""E-HYB Fase 1 (Nivel A, offline) — funciones de fusion pre-registradas (doc 12 §4).

Dual-run (§4.1): se fusionan las salidas de las corridas E-IND y E-DIR YA HECHAS.
Las señales son bit a bit las individuales; toda diferencia es de la fusion.

La fusion no tiene parametros libres propios: hereda los umbrales calibrados en la
mitad A de cada brazo y el IoU de gating es el mismo 0.5 del matching de la Fase 1.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/

from bench.geometry import iou  # noqa: E402


def gate_by_person(edir_preds: list[dict], person_boxes: list[list[float]],
                   iou_thr: float = 0.5) -> list[dict]:
    """Gating por persona (doc 12 §4.2): una prediccion E-DIR solo aporta evidencia
    si matchea (IoU>=0.5) con una persona DETECTADA. Un FP suelto sin persona no
    puede disparar evidencia, y la alerta queda reconstruible ("frase F sobre la
    persona en bbox X")."""
    return [p for p in edir_preds
            if any(iou(p["bbox_xyxy"], pb) >= iou_thr for pb in person_boxes)]


def fuse_or(eind_preds: list[dict], edir_gated: list[dict],
            iou_thr: float = 0.5) -> list[dict]:
    """E-HYB-or (doc 12 §4.3): union gateada, con dedupe.

    Si ambos brazos marcan a la misma persona se emite UNA prediccion (la de E-IND,
    señal primaria y box de persona): sin dedupe, el box duplicado quedaria sin
    persona libre en el matching 1:1 y contaria FP — la fusion se penalizaria a si
    misma por estar de acuerdo.
    """
    fused = list(eind_preds)
    for p in edir_gated:
        if not any(iou(p["bbox_xyxy"], e["bbox_xyxy"]) >= iou_thr for e in eind_preds):
            fused.append(p)
    return fused


def corroboration_split(gt_records: list[dict], eind_preds: list[dict],
                        edir_gated: list[dict], attribute: str,
                        iou_thr: float = 0.5) -> dict:
    """La parte de E-HYB-and medible en Fase 1: ¿a quien corrobora E-DIR?

    -and no cambia quien queda marcado (E-IND es la señal primaria; su efecto —
    acelerar la confirmacion — se ve recien en Nivel B). Lo que Fase 1 SI puede
    medir es la tasa de corroboracion sobre los TPs vs sobre los FPs de E-IND:
    si corrobora mas a los aciertos, acelerar por corroboracion es seguro; si
    corrobora igual a los errores, -and acelera tambien las falsas alertas.

    Mismo matching codicioso 1:1 por confianza que score_person_state.
    """
    usados: set[int] = set()
    stats = {"tp_total": 0, "tp_corroborated": 0, "fp_total": 0, "fp_corroborated": 0}
    for pred in sorted(eind_preds, key=lambda p: -p.get("confidence", 0.0)):
        mejor_i, mejor = None, iou_thr
        for i, rec in enumerate(gt_records):
            if i in usados:
                continue
            v = iou(pred["bbox_xyxy"], rec["person_bbox"])
            if v >= mejor:
                mejor_i, mejor = i, v
        corroborada = any(iou(pred["bbox_xyxy"], e["bbox_xyxy"]) >= iou_thr
                          for e in edir_gated)
        if mejor_i is not None:
            usados.add(mejor_i)
        es_tp = mejor_i is not None and gt_records[mejor_i].get(attribute) is False
        clave = "tp" if es_tp else "fp"
        stats[f"{clave}_total"] += 1
        if corroborada:
            stats[f"{clave}_corroborated"] += 1
    return stats
