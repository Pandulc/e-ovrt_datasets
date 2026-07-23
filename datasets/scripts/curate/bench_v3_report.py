"""Agregado ponderado de resultados de evaluate_perception sobre bench_v3.

No decide el campeón (eso es doc 62 §2: mAP50 agregado, desempate recall
CR-01) — solo pondera por n_gt/n_violators REAL, no por conteo de estratos:
una clase ausente en un estrato (AP50=None, n_gt=0) no debe pesar en el
promedio ni contar como cero.
"""
from __future__ import annotations


def weighted_map50(evals: list[dict], classes: list[str]) -> dict[str, float | None]:
    """Promedia AP50 por clase, ponderado por n_gt de cada estrato."""
    result: dict[str, float | None] = {}
    for cls in classes:
        num = den = 0.0
        for ev in evals:
            entry = next((c for c in ev["per_class"] if c["class_name"] == cls), None)
            if entry is None or entry["AP50"] is None or entry["n_gt"] == 0:
                continue
            num += entry["AP50"] * entry["n_gt"]
            den += entry["n_gt"]
        result[cls] = (num / den) if den > 0 else None
    return result


def weighted_cr01_recall(evals: list[dict]) -> float | None:
    """Pondera el recall CR-01 por cantidad real de violadores por estrato."""
    num = den = 0.0
    for ev in evals:
        recall = ev.get("cr01_detection_recall")
        n = ev.get("cr01_n_violators") or 0
        if recall is None or n == 0:
            continue
        num += recall * n
        den += n
    return (num / den) if den > 0 else None
