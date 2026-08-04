"""Fase D — Fase 1 (Nivel A): E-DIR vs E-IND sobre el bench, a nivel persona.

Ejecuta el protocolo pre-registrado (`nucleo/04` §7 Fase 1):
  1. Parte cada estrato en mitades A/B estratificadas por presencia de violador.
  2. Calibra umbrales SOLO en la mitad A (grid para E-IND, barrido para cada variante
     E-DIR).
  3. Reporta SOLO sobre la mitad B, con IC bootstrap y los conteos de la clase positiva.
  4. Evalua el gate del §8 y mide la complementariedad de errores (insumo E-HYB).

Uso:
  python3 datasets/scripts/bench/run_fase_d_nivel_a.py \
      --runs   <runs.json del runner> \
      --out    <dir de salida>
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/

from bench.fuse_ehyb import corroboration_split, fuse_or, gate_by_person  # noqa: E402
from bench.score_person_state import (  # noqa: E402
    add_counts,
    bootstrap_ci,
    load_detections_by_image,
    match_predictions_to_gt,
    predict_edir,
    predict_eind,
    prf1,
    stratified_halves,
)

REPO = Path(__file__).resolve().parents[2]          # datasets/
MEDIA_RUNS = REPO.parent.parent / "e-ovrt_media-plane" / "runs"

# Regiones del pattern set DESPLEGADO cr01_cr02_v2: E-IND se puntua con la misma
# geometria que usa la plataforma, no con una calibrada para el bench.
CONDICIONES = {
    "CR-01": {
        "attribute": "has_helmet",
        "evidence_label": "helmet",
        "region": {"y_min_ratio": 0.0, "y_max_ratio": 0.45, "x_margin_ratio": 0.12},
        "variants": ["cr01_neg", "cr01_spec", "cr01_obs"],
    },
    "CR-02": {
        "attribute": "has_vest",
        "evidence_label": "vest",
        "region": {"y_min_ratio": 0.25, "y_max_ratio": 0.85, "x_margin_ratio": 0.08},
        "variants": ["cr02_neg", "cr02_spec", "cr02_obs"],
    },
}

# El modelo emite con box_threshold 0.30: por debajo de eso no hay deteccion que
# umbralar. Los grids arrancan ahi y son IDENTICOS para los dos brazos.
# Llegan hasta 0.85 a proposito: con el grid cortado en 0.50/0.60 los DOS brazos
# elegian su valor maximo, o sea que ninguno estaba calibrado en su optimo y la
# comparacion medía el techo del grid, no la estrategia (medido, doc 83).
GRID_PERSON = [0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80]
GRID_EVIDENCE = [0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80]
GRID_EDIR = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]

ESTRATOS = {
    "bench_obra": {
        "run_strata": ["bench_obra_val", "bench_obra_test"],
        "person_gt": "processed/coco/bench/curated/person_gt_bench_obra_v2.json",
        # El universo de imagenes sale del COCO curado, NO de las que tienen personas:
        # si no, las imagenes sin gente quedan fuera y una alucinacion ahi ("person
        # without hard hat" donde no hay nadie) no paga ningun costo.
        "image_universe": [
            "processed/coco/bench/curated/construction_site_safety_bench_obra_val.json",
            "processed/coco/bench/curated/construction_site_safety_bench_obra_test.json",
        ],
        "conditions": ["CR-01", "CR-02"],
    },
    "shel5k": {
        "run_strata": ["shel5k"],
        "person_gt": "processed/coco/bench/curated/person_gt_shel5k.json",
        "image_universe": ["processed/coco/bench/curated/bench_stratum_shel5k.json"],
        "conditions": ["CR-01"],
    },
}


def gt_por_imagen(person_gt: dict) -> dict[str, list[dict]]:
    por_imagen: dict[str, list[dict]] = {}
    for rec in person_gt["records"]:
        por_imagen.setdefault(Path(rec["file_name"]).name, []).append(rec)
    return por_imagen


def _contar(imagenes, gt_img, dets_img, attribute, predecir, **kw) -> dict:
    total = {"tp": 0, "fp": 0, "fn": 0, "n_gt": 0, "n_gt_positive": 0}
    for img in imagenes:
        preds = predecir(dets_img.get(img, []), **kw)
        c = match_predictions_to_gt(gt_img.get(img, []), preds, attribute)
        total = add_counts(total, c)
    return total


def _por_imagen(imagenes, gt_img, dets_img, attribute, predecir, **kw) -> list[dict]:
    """Unidades para el bootstrap: se remuestrean IMAGENES, no personas.

    Las personas de una misma imagen no son independientes (comparten escena, escala y
    condiciones de luz); remuestrearlas sueltas daria un IC optimista.
    """
    return [match_predictions_to_gt(gt_img.get(img, []), predecir(dets_img.get(img, []), **kw),
                                    attribute)
            for img in imagenes]


def calibrar_eind(imagenes_a, gt_img, dets_img, cond) -> dict:
    mejor = None
    for pc in GRID_PERSON:
        for ec in GRID_EVIDENCE:
            c = _contar(imagenes_a, gt_img, dets_img, cond["attribute"], predict_eind,
                        evidence_label=cond["evidence_label"], region=cond["region"],
                        person_conf=pc, evidence_conf=ec)
            m = prf1(c)
            if m["f1"] is None:
                continue
            if mejor is None or m["f1"] > mejor["f1_calib"]:
                mejor = {"person_conf": pc, "evidence_conf": ec, "f1_calib": m["f1"]}
    return mejor or {"person_conf": 0.35, "evidence_conf": 0.30, "f1_calib": None}


def calibrar_edir(imagenes_a, gt_img, dets_img, cond, variant) -> dict:
    mejor = None
    for thr in GRID_EDIR:
        c = _contar(imagenes_a, gt_img, dets_img, cond["attribute"], predict_edir,
                    variant_id=variant, conf=thr)
        m = prf1(c)
        if m["f1"] is None:
            continue
        if mejor is None or m["f1"] > mejor["f1_calib"]:
            mejor = {"conf": thr, "f1_calib": m["f1"]}
    return mejor or {"conf": 0.30, "f1_calib": None}


def personas_erradas(imagenes, gt_img, dets_img, attribute, predecir, **kw) -> set:
    """Claves (imagen, bbox) de violadores del GT que la estrategia NO recupera.

    Insumo del analisis de complementariedad: si los errores de las dos estrategias
    caen en personas distintas, la fusion E-HYB tiene margen; si caen en las mismas,
    no lo tiene.
    """
    fallos = set()
    for img in imagenes:
        recs = gt_img.get(img, [])
        preds = predecir(dets_img.get(img, []), **kw)
        aciertos = set()
        usados = set()
        from bench.geometry import iou as _iou
        for pred in sorted(preds, key=lambda p: -p.get("confidence", 0.0)):
            mejor_i, mejor = None, 0.5
            for i, r in enumerate(recs):
                if i in usados:
                    continue
                v = _iou(pred["bbox_xyxy"], r["person_bbox"])
                if v >= mejor:
                    mejor_i, mejor = i, v
            if mejor_i is not None:
                usados.add(mejor_i)
                if recs[mejor_i].get(attribute) is False:
                    aciertos.add(mejor_i)
        for i, r in enumerate(recs):
            if r.get(attribute) is False and i not in aciertos:
                fallos.add((img, tuple(r["person_bbox"])))
    return fallos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=20260803)
    ap.add_argument("--bootstrap", type=int, default=1000)
    a = ap.parse_args()

    runs = json.loads(a.runs.read_text())
    ok = [r for r in runs if r.get("run_id")]
    print(f"{len(ok)} corridas disponibles")

    resultados = {"seed": a.seed, "strata": {}, "gate": {}, "complementarity": {}}

    for estrato_id, cfg in ESTRATOS.items():
        gt_path = REPO / cfg["person_gt"]
        if not gt_path.exists():
            print(f"[{estrato_id}] sin person_gt ({gt_path}) — se saltea")
            continue
        person_gt = json.loads(gt_path.read_text())
        gt_img = gt_por_imagen(person_gt)

        # Detecciones del brazo E-IND (puede venir de dos corridas: val + test)
        eind_runs = [r for r in ok if r["arm"] == "eind" and r["stratum"] in cfg["run_strata"]]
        if not eind_runs:
            print(f"[{estrato_id}] sin corrida E-IND todavia — se saltea")
            continue
        dets_eind: dict[str, list[dict]] = {}
        for r in eind_runs:
            for k, v in load_detections_by_image(MEDIA_RUNS / r["run_id"]).items():
                dets_eind.setdefault(k, []).extend(v)

        # Universo = imagenes del COCO curado (restringe las 196 del raw a las 147
        # curadas). Las que no tienen personas entran igual, con GT vacio: ahi una
        # prediccion es una alucinacion y cuenta como FP.
        universo: set[str] = set()
        for rel in cfg["image_universe"]:
            coco = json.loads((REPO / rel).read_text())
            universo |= {Path(im["file_name"]).name for im in coco["images"]}
        imagenes = sorted(universo & set(dets_eind))
        con_personas = sum(1 for i in imagenes if gt_img.get(i))
        print(f"[{estrato_id}] {len(imagenes)} imagenes del estrato "
              f"({con_personas} con personas anotadas)")

        resultados["strata"][estrato_id] = {"n_images": len(imagenes), "conditions": {}}

        for cond_id in cfg["conditions"]:
            cond = CONDICIONES[cond_id]
            attr = cond["attribute"]
            # Estratificar la particion por presencia de violador de ESTA condicion.
            items = [(img, "pos" if any(r.get(attr) is False for r in gt_img.get(img, []))
                      else "neg")
                     for img in imagenes]
            mitad_a, mitad_b = stratified_halves(items, seed=a.seed)

            entrada = {"n_calib": len(mitad_a), "n_test": len(mitad_b), "arms": {}}

            # --- E-IND
            cal = calibrar_eind(mitad_a, gt_img, dets_eind, cond)
            counts_b = _contar(mitad_b, gt_img, dets_eind, attr, predict_eind,
                               evidence_label=cond["evidence_label"], region=cond["region"],
                               person_conf=cal["person_conf"], evidence_conf=cal["evidence_conf"])
            unidades = _por_imagen(mitad_b, gt_img, dets_eind, attr, predict_eind,
                                   evidence_label=cond["evidence_label"], region=cond["region"],
                                   person_conf=cal["person_conf"], evidence_conf=cal["evidence_conf"])
            m = prf1(counts_b)
            entrada["arms"]["eind"] = {
                "calibration": cal, "metrics": m,
                "ci_recall": bootstrap_ci(unidades, "recall", a.bootstrap, a.seed),
                "ci_precision": bootstrap_ci(unidades, "precision", a.bootstrap, a.seed),
            }

            # --- E-DIR, una entrada por variante
            dets_por_variante: dict[str, dict] = {}
            for variant in cond["variants"]:
                vruns = [r for r in ok if r["arm"] == "edir" and r["variant"] == variant
                         and r["stratum"] in cfg["run_strata"]]
                if not vruns:
                    continue
                dets_v: dict[str, list[dict]] = {}
                for r in vruns:
                    for k, v in load_detections_by_image(MEDIA_RUNS / r["run_id"]).items():
                        dets_v.setdefault(k, []).extend(v)
                dets_por_variante[variant] = dets_v
                calv = calibrar_edir(mitad_a, gt_img, dets_v, cond, variant)
                cb = _contar(mitad_b, gt_img, dets_v, attr, predict_edir,
                             variant_id=variant, conf=calv["conf"])
                unid = _por_imagen(mitad_b, gt_img, dets_v, attr, predict_edir,
                                   variant_id=variant, conf=calv["conf"])
                entrada["arms"][variant] = {
                    "calibration": calv, "metrics": prf1(cb),
                    "ci_recall": bootstrap_ci(unid, "recall", a.bootstrap, a.seed),
                    "ci_precision": bootstrap_ci(unid, "precision", a.bootstrap, a.seed),
                }

            # --- E-HYB Fase 1 offline (doc 12 §4): dual-run, sin inferencia nueva.
            # La variante que entra a la fusion se elige por f1 de CALIBRACION
            # (mitad A) — elegirla por el f1 de test seria mirar la respuesta.
            variantes_cal = {k: v for k, v in entrada["arms"].items() if k != "eind"}
            if variantes_cal:
                var_fusion = max(variantes_cal,
                                 key=lambda k: variantes_cal[k]["calibration"].get("f1_calib") or 0.0)
                conf_v = variantes_cal[var_fusion]["calibration"]["conf"]
                dets_v = dets_por_variante[var_fusion]

                def _preds_fusion(img):
                    eind_p = predict_eind(
                        dets_eind.get(img, []), cond["evidence_label"], cond["region"],
                        cal["person_conf"], cal["evidence_conf"])
                    # Personas detectadas para el gating §4.2: las del run E-IND por
                    # encima del umbral de sujeto calibrado (en dual-run son las
                    # unicas cajas de persona que existen).
                    personas = [d["bbox_xyxy"] for d in dets_eind.get(img, [])
                                if d["label"] == "person"
                                and d["confidence"] >= cal["person_conf"]]
                    edir_g = gate_by_person(
                        predict_edir(dets_v.get(img, []), var_fusion, conf_v), personas)
                    return eind_p, edir_g

                total = {"tp": 0, "fp": 0, "fn": 0, "n_gt": 0, "n_gt_positive": 0}
                unidades_or = []
                corr = {"tp_total": 0, "tp_corroborated": 0, "fp_total": 0, "fp_corroborated": 0}
                for img in mitad_b:
                    eind_p, edir_g = _preds_fusion(img)
                    c = match_predictions_to_gt(gt_img.get(img, []),
                                                fuse_or(eind_p, edir_g), attr)
                    unidades_or.append(c)
                    total = add_counts(total, c)
                    s = corroboration_split(gt_img.get(img, []), eind_p, edir_g, attr)
                    for k in corr:
                        corr[k] += s[k]
                entrada["arms"]["ehyb_or"] = {
                    "calibration": {"edir_variant": var_fusion, "edir_conf": conf_v,
                                    "person_conf": cal["person_conf"],
                                    "evidence_conf": cal["evidence_conf"],
                                    "note": "sin parametros libres propios: hereda los umbrales calibrados de cada brazo"},
                    "metrics": prf1(total),
                    "ci_recall": bootstrap_ci(unidades_or, "recall", a.bootstrap, a.seed),
                    "ci_precision": bootstrap_ci(unidades_or, "precision", a.bootstrap, a.seed),
                }
                entrada["ehyb_and_corroboration"] = {
                    "edir_variant": var_fusion,
                    **corr,
                    "tp_rate": (corr["tp_corroborated"] / corr["tp_total"]) if corr["tp_total"] else None,
                    "fp_rate": (corr["fp_corroborated"] / corr["fp_total"]) if corr["fp_total"] else None,
                    "note": ("-and no cambia el estado por persona (E-IND primaria); esto mide "
                             "si la corroboracion distingue aciertos de errores — el insumo de "
                             "seguridad para el corroboration_factor de Nivel B"),
                }

            resultados["strata"][estrato_id]["conditions"][cond_id] = entrada

            # --- Gate del §8 y complementariedad, sobre la mitad B.
            # Solo variantes E-DIR: la fusion ehyb_or no compite en el gate (sus
            # criterios de adopcion son los del §8.3, sobre F1 de ALERTAS en Fase 2).
            f1_eind = entrada["arms"]["eind"]["metrics"]["f1"]
            variantes = {k: v for k, v in entrada["arms"].items()
                         if k not in ("eind", "ehyb_or")}
            if variantes and f1_eind:
                mejor_var = max(variantes, key=lambda k: variantes[k]["metrics"]["f1"] or 0.0)
                f1_edir = variantes[mejor_var]["metrics"]["f1"]
                resultados["gate"][f"{estrato_id}/{cond_id}"] = {
                    "f1_eind": f1_eind, "best_edir_variant": mejor_var, "f1_edir": f1_edir,
                    "ratio": (f1_edir / f1_eind) if f1_eind else None,
                    "edir_below_half": bool(f1_edir < 0.5 * f1_eind),
                }
                fallos_eind = personas_erradas(
                    mitad_b, gt_img, dets_eind, attr, predict_eind,
                    evidence_label=cond["evidence_label"], region=cond["region"],
                    person_conf=cal["person_conf"], evidence_conf=cal["evidence_conf"])
                vruns = [r for r in ok if r["arm"] == "edir" and r["variant"] == mejor_var
                         and r["stratum"] in cfg["run_strata"]]
                dets_v = {}
                for r in vruns:
                    for k, v in load_detections_by_image(MEDIA_RUNS / r["run_id"]).items():
                        dets_v.setdefault(k, []).extend(v)
                fallos_edir = personas_erradas(mitad_b, gt_img, dets_v, attr, predict_edir,
                                               variant_id=mejor_var,
                                               conf=variantes[mejor_var]["calibration"]["conf"])
                recuperados = fallos_eind - fallos_edir
                resultados["complementarity"][f"{estrato_id}/{cond_id}"] = {
                    "best_edir_variant": mejor_var,
                    "eind_misses": len(fallos_eind),
                    "edir_misses": len(fallos_edir),
                    "recovered_by_edir": len(recuperados),
                    "fraction_recovered": (len(recuperados) / len(fallos_eind)) if fallos_eind else None,
                }

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "metrics.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    print(f"\n-> {a.out / 'metrics.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
