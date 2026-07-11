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
    """Resultado completo de la comparación entre dos anotadores.

    FIX 5 (auditoría 2026-07-11): si `duration_ms` difiere entre los dos GT,
    no son derivaciones del mismo clip preparado (recortes distintos) —
    antes `window_states` truncaba en silencio a la duración de cada GT por
    separado, mezclando ventanas que no correspondían al mismo instante y
    produciendo un kappa/deltas engañosos. Acá se falla ruidosamente.
    """
    if gt_a["duration_ms"] != gt_b["duration_ms"]:
        raise ValueError(
            f"duration_ms no coincide entre los dos GT ({gt_a.get('clip_id')}: "
            f"{gt_a['duration_ms']} ms vs {gt_b.get('clip_id')}: "
            f"{gt_b['duration_ms']} ms) — no son del mismo clip preparado"
        )
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
