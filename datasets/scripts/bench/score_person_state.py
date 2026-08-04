"""Scoring de estado por persona para la Fase D — Fase 1 (Nivel A).

Pre-registro `nucleo/04` §7 Fase 1. Puntua el estado "sin EPP" a nivel PERSONA contra
`has_helmet` / `has_vest`, para las dos estrategias de prompts:

  E-IND — `spatial_absence` aplicado offline sobre detecciones positivas
          (person + helmet/vest), con la region del pattern set desplegado
          `cr01_cr02_v2`. Es literalmente lo que hace la plataforma.
  E-DIR — la deteccion de la variante ES la prediccion de persona-en-violacion; se
          matchea por IoU contra la persona del GT.

Reglas que el modulo hace cumplir:
  - Las dos estrategias se puntuan sobre EL MISMO conjunto de personas del GT. Una
    persona que ningun detector encontro es fallo para ambas.
  - Matching 1:1 codicioso por confianza: una caja no puede acertarle a dos personas.
  - Umbrales calibrados en la mitad A, metricas reportadas SOLO sobre la mitad B.
  - `precision` sin predicciones y `recall` sin positivos quedan en None, nunca en un
    0.0 o 1.0 que despues se promedia como si fuera una medicion.
"""
import json
import random
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # datasets/scripts/

from bench.geometry import iou  # noqa: E402


# ---------------------------------------------------------------------------
# Geometria de region (identica a _region_bbox del control-plane)
# ---------------------------------------------------------------------------

def region_bbox(person_xyxy: list[float], region: dict) -> list[float]:
    """Sub-region del cuerpo donde se busca la evidencia de EPP.

    Misma aritmetica que `engine/evaluators/spatial_absence.py::_region_bbox`: si esto
    diverge, el numero de Nivel A deja de predecir el de Nivel B.
    """
    x1, y1, x2, y2 = person_xyxy
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    margin_x = width * region["x_margin_ratio"]
    return [
        x1 + margin_x,
        y1 + height * region["y_min_ratio"],
        x2 - margin_x,
        y1 + height * region["y_max_ratio"],
    ]


def _center(box: list[float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _center_inside(box: list[float], region: list[float]) -> bool:
    cx, cy = _center(box)
    return region[0] <= cx <= region[2] and region[1] <= cy <= region[3]


# ---------------------------------------------------------------------------
# Prediccion por estrategia
# ---------------------------------------------------------------------------

def predict_eind(
    detections: list[dict],
    evidence_label: str,
    region: dict,
    person_conf: float,
    evidence_conf: float,
) -> list[dict]:
    """Personas predichas EN VIOLACION por E-IND (spatial_absence offline)."""
    persons = [d for d in detections
               if d["label"] == "person" and d["confidence"] >= person_conf]
    evidencia = [d for d in detections
                 if d["label"] == evidence_label and d["confidence"] >= evidence_conf]
    violaciones = []
    for p in persons:
        reg = region_bbox(p["bbox_xyxy"], region)
        if not any(_center_inside(e["bbox_xyxy"], reg) for e in evidencia):
            violaciones.append({"bbox_xyxy": p["bbox_xyxy"], "confidence": p["confidence"]})
    return violaciones


def predict_edir(detections: list[dict], variant_id: str, conf: float) -> list[dict]:
    """Personas predichas EN VIOLACION por una variante E-DIR (la deteccion es la prediccion)."""
    return [{"bbox_xyxy": d["bbox_xyxy"], "confidence": d["confidence"]}
            for d in detections
            if d.get("prompt_id") == variant_id and d["confidence"] >= conf]


# ---------------------------------------------------------------------------
# Matching prediccion <-> GT
# ---------------------------------------------------------------------------

def match_predictions_to_gt(
    gt_records: list[dict],
    predictions: list[dict],
    attribute: str,
    iou_thr: float = 0.5,
    skip_ambiguous_vest: bool = False,
) -> dict:
    """Confusion a nivel persona para una condicion.

    `attribute` es 'has_helmet' o 'has_vest'; la clase POSITIVA es la violacion
    (atributo False). Matching codicioso 1:1 ordenado por confianza: una prediccion
    consume a lo sumo una persona, para que una caja grande no "acierte" una multitud.

    Con `skip_ambiguous_vest`, las personas cuya atribucion de negativo de chaleco fue
    ambigua (doc 83) salen del calculo: es el analisis de sensibilidad de esa decision.
    """
    activos = [
        (i, r) for i, r in enumerate(gt_records)
        if not (skip_ambiguous_vest and r.get("vest_attribution_ambiguous"))
    ]
    tp = fp = fn = 0
    usados: set[int] = set()
    ordenadas = sorted(predictions, key=lambda p: -p.get("confidence", 0.0))
    for pred in ordenadas:
        mejor_i, mejor_iou = None, iou_thr
        for i, rec in activos:
            if i in usados:
                continue
            v = iou(pred["bbox_xyxy"], rec["person_bbox"])
            if v >= mejor_iou:
                mejor_i, mejor_iou = i, v
        if mejor_i is None:
            fp += 1                                   # prediccion sin persona: alucinacion
            continue
        usados.add(mejor_i)
        rec = gt_records[mejor_i]
        if rec.get(attribute) is False:
            tp += 1                                   # violador detectado
        else:
            fp += 1                                   # cumplidor marcado como violador
    for i, rec in activos:
        if i not in usados and rec.get(attribute) is False:
            fn += 1                                   # violador que nadie encontro
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "n_gt": len(activos),
        "n_gt_positive": sum(1 for _, r in activos if r.get(attribute) is False),
    }


def add_counts(a: dict, b: dict) -> dict:
    return {k: a.get(k, 0) + b.get(k, 0) for k in ("tp", "fp", "fn", "n_gt", "n_gt_positive")}


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------

def prf1(counts: dict) -> dict:
    """precision/recall/F1. None cuando el denominador no existe (no 0.0 ni 1.0).

    Sin predicciones la precision es INDEFINIDA, no perfecta; sin positivos en el GT
    el recall es INDEFINIDO, no cero. Promediar esos casos como numeros es el error
    F-EV1 del doc 81, en otra escala.
    """
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    if precision is None and recall is None:
        f1 = None
    elif not precision or not recall:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn,
            "n_gt": counts.get("n_gt"), "n_gt_positive": counts.get("n_gt_positive")}


# ---------------------------------------------------------------------------
# Particion calib/test
# ---------------------------------------------------------------------------

def stratified_halves(items: list[tuple], seed: int = 20260803) -> tuple[list, list]:
    """Mitades A/B estratificadas por clave. `items` = [(id, clave_de_estrato), ...].

    Determinista por semilla: la particion se declara en el campaign.yaml y tiene que
    poder reproducirse. La mitad A calibra, la B reporta — nunca la misma.
    """
    por_clave: dict = {}
    for item_id, clave in items:
        por_clave.setdefault(clave, []).append(item_id)
    rng = random.Random(seed)
    a, b = [], []
    for clave in sorted(por_clave):
        grupo = sorted(por_clave[clave])
        rng.shuffle(grupo)
        mitad = len(grupo) // 2
        a.extend(grupo[:mitad])
        b.extend(grupo[mitad:])
    return sorted(a), sorted(b)


def sweep_best_threshold(thresholds: list[float], score_at) -> dict:
    """Umbral que maximiza F1. Los umbrales con F1 indefinido no compiten."""
    mejor = None
    for thr in thresholds:
        m = score_at(thr)
        f1 = m.get("f1")
        if f1 is None:
            continue
        if mejor is None or f1 > mejor["f1"]:
            mejor = {"threshold": thr, "f1": f1, "metrics": m}
    return mejor if mejor is not None else {"threshold": None, "f1": None, "metrics": {}}


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap_ci(
    units: list[dict],
    metric: str,
    n_iter: int = 1000,
    seed: int = 20260803,
    alpha: float = 0.05,
) -> dict:
    """IC percentil por remuestreo de unidades (personas o imagenes) con reemplazo."""
    rng = random.Random(seed)
    n = len(units)
    valores = []
    for _ in range(n_iter):
        muestra = [units[rng.randrange(n)] for _ in range(n)]
        agregado = {"tp": 0, "fp": 0, "fn": 0}
        for u in muestra:
            for k in agregado:
                agregado[k] += u.get(k, 0)
        v = prf1(agregado)[metric]
        if v is not None:
            valores.append(v)
    if not valores:
        return {"lo": None, "hi": None, "n_iter": n_iter}
    valores.sort()
    lo = valores[int(alpha / 2 * len(valores))]
    hi = valores[min(len(valores) - 1, int((1 - alpha / 2) * len(valores)))]
    return {"lo": lo, "hi": hi, "n_iter": n_iter}


# ---------------------------------------------------------------------------
# Carga de detecciones
# ---------------------------------------------------------------------------

def load_detections_by_image(run_dir: Path) -> dict[str, list[dict]]:
    """basename de imagen -> detecciones, desde el detections.jsonl de una corrida."""
    por_imagen: dict[str, list[dict]] = {}
    path = Path(run_dir) / "detections.jsonl"
    with path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            ev = json.loads(line)
            clave = Path(ev["source"]["source_id"]).name
            por_imagen.setdefault(clave, []).extend(ev.get("detections", []))
    return por_imagen
