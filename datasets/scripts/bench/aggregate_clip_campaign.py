"""Agrega una CAMPAÑA sobre el banco de clips a métricas listas para el informe.

Una **campaña** es una corrida del banco completo con UNA combinación declarada
(modelo × prompt set × pattern set × granularidad × camino). El punto de este
script es que cada campaña produzca un `metrics.json` con la MISMA forma, para
que comparar dos combinaciones sea leer dos archivos y no rehacer aritmética a
mano (que es donde se cuelan los errores que el doc 81 §3 documenta).

Reglas de agregación, todas con test:

- **Los clips negativos NO entran a precision/recall/F1** — su
  `applicability_state` es `not_applicable:negative_clip_no_episodes` (F-EV1) y
  promediarlos hundiría el agregado contando aciertos como catástrofes. Entran al
  **control de falsos positivos**, que es su métrica.
- **Los episodios censurados salen del denominador de recall** (A2, doc 57 §6.7).
- **Las `re_alerts` no son FP** (ADR-011).
- **Siempre se emite el desglose por escenario** (limitación L5 de
  `registry/clip_bench.md`: el agregado está dominado por P1/P2).
- **Micro y macro se distinguen**: con escenarios desbalanceados no coinciden, y
  el informe tiene que decir cuál usa. Micro = por episodio (el que se reporta
  por defecto); macro = media de los recalls por clip.
- **FAR/hora solo con clips soak** (≥5 min, doc 57 §3.2 G1). Sin ellos queda
  `None` con la base declarada, nunca un 0.0 que parezca medido.

Uso:
    python3 datasets/scripts/bench/aggregate_clip_campaign.py \\
        --evals-dir <dir con eval_<clip>.json> \\
        --gt-dir datasets-videos/gt \\
        --out <campaña>/metrics.json [--campaign <campaign.yaml>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

SOAK_MIN_MS = 5 * 60 * 1000  # doc 57 §3.2 G1
FAR_BASIS = "solo clips soak (negativos >= 5 min, doc 57 §3.2 G1)"


def _safe(num: float, den: float):
    return round(num / den, 6) if den else None


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(mean(xs), 6) if xs else None


def _load(evals_dir: Path, gt_dir: Path) -> list[dict]:
    rows = []
    for p in sorted(Path(evals_dir).glob("eval_*.json")):
        e = json.loads(p.read_text())
        clip_id = e.get("scenario_id") or p.stem.replace("eval_", "")
        gt_path = Path(gt_dir) / f"{clip_id}.json"
        if not gt_path.exists():
            raise ValueError(
                f"{p.name}: clip {clip_id!r} sin GT en {gt_dir} — un eval sin su "
                "GT no se puede agregar (no se sabe escenario ni condiciones)"
            )
        rows.append({"clip_id": clip_id, "eval": e, "gt": json.loads(gt_path.read_text())})
    if not rows:
        raise ValueError(f"no se encontro ningun eval_*.json en {evals_dir}")
    return rows


def _clip_recall(e: dict):
    den = e["expected_alerts_count"] - e.get("censored_episodes_count", 0)
    return _safe(e["matched_alerts_count"], den)


def aggregate_campaign(evals_dir, gt_dir, campaign: dict | None = None) -> dict:
    """-> dict con `positives`, `negatives`, `by_condition`, `by_scenario`, `by_clip`."""
    rows = _load(evals_dir, gt_dir)
    pos = [r for r in rows if r["eval"]["expected_alerts_count"] > 0]
    neg = [r for r in rows if r["eval"]["expected_alerts_count"] == 0]

    def tot(rs, key, default=0):
        return sum(r["eval"].get(key, default) for r in rs)

    ep = tot(pos, "expected_alerts_count")
    cen = tot(pos, "censored_episodes_count")
    mat = tot(pos, "matched_alerts_count")
    fp = tot(pos, "unexpected_alerts_count")
    evaluable = ep - cen

    positives = {
        "clips": len(pos),
        "episodes_total": ep,
        "episodes_censored": cen,
        "episodes_evaluable": evaluable,
        "matched": mat,
        "missed": tot(pos, "missed_alerts_count"),
        "false_positives": fp,
        "re_alerts": tot(pos, "re_alerts_count"),
        "sub_threshold": tot(pos, "sub_threshold_count"),
        "recall_micro": _safe(mat, evaluable),
        "precision_micro": _safe(mat, mat + fp),
        "recall_macro": _mean([_clip_recall(r["eval"]) for r in pos]),
        "t_alert_system_ms": _mean([r["eval"].get("avg_latency_ms_from_episode_start") for r in pos]),
        "ttfd_ms": _mean([r["eval"].get("avg_ttfd_ms") for r in pos]),
        "sdr": _mean([r["eval"].get("avg_sdr") for r in pos]),
    }
    rm, pm = positives["recall_micro"], positives["precision_micro"]
    positives["f1_micro"] = (
        round(2 * rm * pm / (rm + pm), 6) if rm and pm and (rm + pm) else None
    )

    neg_ms = sum(r["gt"].get("duration_ms") or 0 for r in neg)
    soak_ms = sum(d for r in neg if (d := r["gt"].get("duration_ms") or 0) >= SOAK_MIN_MS)
    neg_fp = tot(neg, "unexpected_alerts_count")
    negatives = {
        "clips": len(neg),
        "false_positives": neg_fp,
        "observed_ms": neg_ms,
        "soak_clips": sum(1 for r in neg if (r["gt"].get("duration_ms") or 0) >= SOAK_MIN_MS),
        "soak_ms": soak_ms,
        "far_per_hour": _safe(neg_fp, soak_ms / 3_600_000.0) if soak_ms else None,
        "far_basis": FAR_BASIS,
    }

    by_condition: dict[str, dict] = {}
    for r in pos:
        for epi in r["gt"]["episodes"]:
            c = by_condition.setdefault(
                epi["condition_id"], {"episodes": 0, "clips": set()})
            c["episodes"] += 1
            c["clips"].add(r["clip_id"])
    for cond, c in by_condition.items():
        clips = [r for r in pos if r["clip_id"] in c["clips"]]
        c["clips"] = len(c["clips"])
        c["sdr"] = _mean([r["eval"].get("avg_sdr") for r in clips])
        c["t_alert_system_ms"] = _mean(
            [r["eval"].get("avg_latency_ms_from_episode_start") for r in clips])
        c["false_positives"] = sum(r["eval"]["unexpected_alerts_count"] for r in clips)

    by_scenario: dict[str, dict] = {}
    for r in rows:
        esc = r["gt"].get("scenario") or "?"
        s = by_scenario.setdefault(esc, {"clips": 0, "positive_clips": 0,
                                         "episodes_evaluable": 0, "matched": 0,
                                         "false_positives": 0, "_sdr": []})
        e = r["eval"]
        s["clips"] += 1
        s["false_positives"] += e["unexpected_alerts_count"]
        if e["expected_alerts_count"] > 0:
            s["positive_clips"] += 1
            s["episodes_evaluable"] += e["expected_alerts_count"] - e.get("censored_episodes_count", 0)
            s["matched"] += e["matched_alerts_count"]
            s["_sdr"].append(e.get("avg_sdr"))
    for s in by_scenario.values():
        s["recall"] = _safe(s["matched"], s["episodes_evaluable"])
        s["sdr"] = _mean(s.pop("_sdr"))

    by_clip = [{
        "clip_id": r["clip_id"],
        "scenario": r["gt"].get("scenario"),
        "conditions": sorted({e["condition_id"] for e in r["gt"]["episodes"]}),
        "expected": r["eval"]["expected_alerts_count"],
        "matched": r["eval"]["matched_alerts_count"],
        "missed": r["eval"]["missed_alerts_count"],
        "censored": r["eval"].get("censored_episodes_count", 0),
        "false_positives": r["eval"]["unexpected_alerts_count"],
        "re_alerts": r["eval"].get("re_alerts_count", 0),
        "recall": _clip_recall(r["eval"]),
        "t_alert_system_ms": r["eval"].get("avg_latency_ms_from_episode_start"),
        "ttfd_ms": r["eval"].get("avg_ttfd_ms"),
        "sdr": r["eval"].get("avg_sdr"),
        "applicability": r["eval"]["applicability_state"],
        "applicability_cause": r["eval"].get("applicability_cause"),
    } for r in rows]

    out = {
        "schema_version": "clip_campaign_metrics.v1",
        "clips_total": len(rows),
        "positives": positives,
        "negatives": negatives,
        "by_condition": dict(sorted(by_condition.items())),
        "by_scenario": dict(sorted(by_scenario.items())),
        "by_clip": by_clip,
        "notes": [
            "Los clips negativos NO entran a precision/recall/F1 (F-EV1): son control de FP.",
            "Los episodios censurados salen del denominador de recall (A2, doc 57 §6.7).",
            "Las re_alerts no cuentan como FP (ADR-011).",
            "Reportar SIEMPRE by_scenario junto al agregado (L5, registry/clip_bench.md).",
            "recall_micro = por episodio; recall_macro = media por clip. Declarar cual se usa.",
        ],
    }
    if campaign:
        out["campaign"] = campaign
    return out


def _fmt(v, w=7, p=3):
    return " " * (w - 1) + "—" if v is None else f"{v:{w}.{p}f}"


def print_summary(m: dict) -> None:
    p, n = m["positives"], m["negatives"]
    c = m.get("campaign") or {}
    if c:
        print(f"CAMPAÑA {c.get('campaign_id','?')}: {c.get('description','')}")
        for k in ("model", "prompt_set", "pattern_set", "granularity", "path"):
            if k in c:
                print(f"  {k:12} = {c[k]}")
    print(f"\nPOSITIVOS: {p['clips']} clips, {p['episodes_total']} episodios "
          f"({p['episodes_censored']} censurados → {p['episodes_evaluable']} evaluables)")
    print(f"  recall  micro={_fmt(p['recall_micro'])}   macro={_fmt(p['recall_macro'])}")
    print(f"  precision micro={_fmt(p['precision_micro'])}   F1={_fmt(p['f1_micro'])}")
    print(f"  matched={p['matched']} missed={p['missed']} FP={p['false_positives']} "
          f"re_alerts={p['re_alerts']}")
    print(f"  t_alert={_fmt(p['t_alert_system_ms'],9,1)} ms   "
          f"TTFD={_fmt(p['ttfd_ms'],7,1)} ms   SDR={_fmt(p['sdr'])}")
    print(f"\nNEGATIVOS (control de FP): {n['clips']} clips, {n['false_positives']} FP, "
          f"{n['observed_ms']/60000:.1f} min")
    print(f"  FAR/hora = {n['far_per_hour'] if n['far_per_hour'] is not None else 'NO REPORTABLE'}"
          f"  ({n['far_basis']}; soak={n['soak_clips']} clips)")
    print(f"\n{'esc':>4} {'clips':>5} {'eps':>4} {'recall':>7} {'FP':>3} {'SDR':>7}")
    for esc, s in m["by_scenario"].items():
        print(f"{esc:>4} {s['clips']:>5} {s['episodes_evaluable']:>4} "
              f"{_fmt(s['recall'])} {s['false_positives']:>3} {_fmt(s['sdr'])}")
    print(f"\n{'cond':>6} {'clips':>5} {'eps':>4} {'FP':>3} {'SDR':>7} {'t_alert':>9}")
    for cond, d in m["by_condition"].items():
        print(f"{cond:>6} {d['clips']:>5} {d['episodes']:>4} {d['false_positives']:>3} "
              f"{_fmt(d['sdr'])} {_fmt(d['t_alert_system_ms'],9,0)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evals-dir", required=True)
    ap.add_argument("--gt-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--campaign", default=None, help="campaign.yaml con la combinacion")
    a = ap.parse_args(argv)

    campaign = None
    if a.campaign:
        import yaml
        campaign = yaml.safe_load(Path(a.campaign).read_text())

    try:
        m = aggregate_campaign(a.evals_dir, a.gt_dir, campaign)
    except ValueError as e:
        ap.error(str(e))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
    print_summary(m)
    print(f"\n✓ {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
