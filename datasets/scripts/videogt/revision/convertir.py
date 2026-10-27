"""Convierte las respuestas de una revisión dirigida en correcciones firmadas — corrida en seco.

NO toca nada del laboratorio. Para cada caso: genera las correcciones, las aplica sobre COPIAS
con las herramientas reales (`apply_identity_corrections`, `apply_attribute_corrections`),
re-deriva el GT con `derive_clip_gt` y escribe, en `datasets-videos/review/<revision>/`:

  propuesta.md                 qué implica cada respuesta y el GT antes/después (para aprobar)
  correcciones/<clip>.yaml     las listas a agregar bajo `annotation:` en <clip>.clip.yaml

Reglas (deterministas; cada corrección cita la regla y la respuesta que la origina):

  R1  Identidad. Caja respondida «P» → sus cajas pasan a la trayectoria principal de P
      (`reassign`); si P ya tiene caja en esos cuadros es una caja duplicada (`drop`).
      «No es una persona» → `drop`. «Q», «Otra» o «No se distingue» → no se toca, salvo que
      sea una caja suelta sin cierre (`close`). «Cambia de persona» → seguimiento manual.
  R2  Intercambio por cuadro (`quien_por_cuadro`). El cambio se ubica en el primer cuadro con
      un cambio de atributo anotado entre la última muestra «Q» y la primera «P»; si no hay, en
      el cuadro siguiente a la última muestra «Q». El tramo «P» se reasigna a P.
  R3  Tramo tapado. «Sigue en cuadro, tapado» → los cuadros sin caja de P dentro del tramo
      (±0,5 s) se rellenan (`fill`, occluded) con los valores de las preguntas `valor_tapado`.
      «Sale de cuadro» o «No se puede saber» → el hueco queda. «Mixto» → seguimiento manual.
  R4  Oclusión breve (protocolo §7.1). En la trayectoria de P reconstruida, un hueco de hasta
      15 cuadros (0,5 s) entre dos cajas con los MISMOS valores de casco y chaleco se rellena
      con esos valores.
  R5  Atributo por cuadro. «Lo lleva» → true; «No lo lleva» / «sin casco» → false; «No se
      puede saber», «no se le ve la cabeza», «No está en cuadro» → unknown; «Tapado (sigue
      igual)» → el valor de la muestra anterior (o de la siguiente, si es la primera). Entre
      dos muestras, cada cuadro toma el valor de la muestra SIGUIENTE: un cambio queda en el
      primer cuadro después de la última muestra con el valor anterior (protocolo §7.2:
      primer cuadro plausible; precisión = el paso de la muestra, ≤ 100 ms). Donde la
      trayectoria no tiene caja y la persona se ve (true/false) → `fill` sin oclusión, con el
      otro atributo en unknown.

Uso:
    python3 datasets/scripts/videogt/revision/convertir.py \
        --spec datasets-videos/docs/revision-dirigida-2026-10.yaml
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
LAB = REPO / "datasets-videos"
BANK_GT = REPO / "datasets/processed/clip_bench/gt"
sys.path.insert(0, str(REPO / "datasets/scripts"))
from videogt.apply_attribute_corrections import apply_corrections  # noqa: E402
from videogt.apply_identity_corrections import apply_identity  # noqa: E402
from videogt.derive_clip_gt import derive  # noqa: E402

PATTERN_SET = {"CR-01": 4000, "CR-02": 7000}
ATTRS = ("has_helmet", "has_vest")
GAP_71 = 15
MAPA = {"puesto": "true", "no_puesto": "false", "no_se_sabe": "unknown", "sin_cabeza": "unknown",
        "fuera": "unknown"}


def ms(f: int, fps: int) -> str:
    return f"{f / fps:.2f}".replace(".", ",") + " s"


def tracks_state(xml_path: Path):
    """{tid: {frame: {attr: valor}}} de cajas visibles; set de tids sueltos sin cierre; stop_frame."""
    root = ET.parse(xml_path).getroot()
    size = root.findtext("./meta/task/size") or root.findtext("./meta/job/size")
    stop = int(size) - 1 if size else None
    out, sueltas = {}, set()
    for tr in root.findall("track"):
        tid = int(tr.get("id"))
        vis = {}
        outs = set()
        for b in tr.findall("box"):
            f = int(b.get("frame"))
            if b.get("outside") == "1":
                outs.add(f)
            else:
                vis[f] = {a.get("name"): (a.text or "").strip().lower() for a in b.findall("attribute")}
        if vis:
            out[tid] = vis
            last = max(vis)
            if (stop is None or last < stop) and (last + 1) not in outs:
                sueltas.add(tid)
    return out, sueltas, stop


def runs(frames):
    out = []
    for f in sorted(frames):
        if out and f == out[-1][1] + 1:
            out[-1][1] = f
        else:
            out.append([f, f])
    return [tuple(r) for r in out]


class Caso:
    def __init__(self, spec_caso, casos_json_caso, R, fps):
        self.s, self.c, self.R, self.fps = spec_caso, casos_json_caso, R, fps
        self.clip = spec_caso["clip"]
        self.id = spec_caso["id"]
        self.firma = {"decided_by": R.get("revisor") or "SIN_FIRMA",
                      "decided_at": (R.get("terminado_en") or R.get("guardado") or "")[:10]}
        self.ops, self.attr_corr, self.seguimiento, self.lineas = [], [], [], []
        self.alias = {}
        self.tramo = None

    def resp(self, qid):
        return self.R.get("respuestas", {}).get(f"{self.id}.{qid}", {})

    def q_spec(self, qid):
        return next(q for q in self.s["preguntas"] if q["id"] == qid)

    def q_json(self, qid):
        return next(q for q in self.c["preguntas"] if q["id"] == f"{self.id}.{qid}")

    def opt_text(self, qid, k):
        qj = self.q_json(qid)
        return next((o["t"] for o in qj["opciones"] if o["k"] == k), k)

    def rationale(self, regla, texto):
        origen = (f"asistida por IA: respuestas propuestas por Claude y validadas por {self.firma['decided_by']}"
                  if self.R.get("propuesta_claude") else f"respuestas de {self.firma['decided_by']}")
        return (f"Revisión dirigida 2026-10 ({origen}; registro en datasets/registry/revision_dirigida_2026-10/), "
                f"caso {self.id} ({self.clip}), {regla}: {texto}")

    # ---------------------------------------------------------------- identidad
    def identidad(self, xml: Path):
        st, sueltas, stop = tracks_state(xml)
        P = self.s.get("persona_p")
        if P is None:
            return
        p_frames = dict(st[P])  # frame -> attrs
        orden = []
        for q in self.s["preguntas"]:
            if q["tipo"] == "identidad":
                for t in q["tracks"]:
                    orden.append((min(st[t]), t, q))
            if q.get("rol") == "quien_por_cuadro":
                orden.append((min(st[q["track"]]), q["track"], q))
        for _, t, q in sorted(orden, key=lambda x: x[0]):
            ans = self.resp(q["id"])
            if q["tipo"] == "identidad":
                a = ans.get(str(t))
                letra = next(it["letra"] for it in self.q_json(q["id"])["items"] if it["id"] == str(t))
                if a is None:
                    self.seguimiento.append(f"caja {letra} ({t}): sin respuesta")
                    continue
                txt = f"la caja {letra} (trayectoria {t}) fue respondida «{self.opt_text(q['id'], a)}»"
                if a == "P":
                    fr = set(st[t])
                    choque = fr & set(p_frames)
                    if not choque:
                        self.ops.append({"op": "reassign", "from_track": t, "to_track": P, "from_frame": min(fr),
                                         "to_frame": max(fr), "boxes": len(fr), **self.firma,
                                         "rationale": self.rationale("R1", txt + "; es la misma persona, va en la "
                                                                     "misma trayectoria (protocolo §7.1, regla C1)")})
                        p_frames.update(st[t])
                        self.alias[t] = P
                    elif choque == fr:
                        self.ops.append({"op": "drop", "track": t, "boxes": len(fr), **self.firma,
                                         "rationale": self.rationale("R1", txt + "; P ya tiene caja en esos cuadros: "
                                                                     "caja duplicada")})
                        self.alias[t] = P
                    else:
                        self.seguimiento.append(f"caja {letra} ({t}) es P pero se superpone en parte con P")
                elif a == "no_persona":
                    self.ops.append({"op": "drop", "track": t, "boxes": len(st[t]), **self.firma,
                                     "rationale": self.rationale("R1", txt)})
                elif a == "cambia":
                    self.seguimiento.append(f"caja {letra} ({t}): cambia de persona — requiere decisión por cuadro")
                elif t in sueltas:
                    self.ops.append({"op": "close", "track": t, **self.firma,
                                     "rationale": self.rationale("R1", txt + "; caja suelta sin cierre: CVAT la "
                                                                 "extiende hasta el final del clip")})
            else:  # quien_por_cuadro
                # «No se distingue» no cuenta ni a favor ni en contra: se descarta.
                lab = {int(k): v for k, v in ans.items() if v != "no_se_sabe"}
                if not lab:
                    self.seguimiento.append(f"trayectoria {t}: sin respuestas de identidad por cuadro")
                    continue
                fs = sorted(lab)
                p_idx = [i for i, f in enumerate(fs) if lab[f] == "P"]
                if not p_idx:
                    continue
                i0 = p_idx[0]
                if any(lab[f] != "P" for f in fs[i0:]):
                    self.seguimiento.append(f"trayectoria {t}: las muestras «P» no son un tramo final continuo")
                    continue
                if i0 == 0:
                    swap = min(st[t])
                else:
                    sq, sp = fs[i0 - 1], fs[i0]
                    # P no puede estar en dos cajas a la vez: el cambio no cae antes de que
                    # termine la trayectoria previa de P.
                    previas = [g for g in p_frames if g < sp]
                    lower = max(sq + 1, (max(previas) + 1) if previas else sq + 1)
                    cambios = [f for f in range(lower, sp + 1) if f in st[t] and f - 1 in st[t]
                               and any(st[t][f].get(a) != st[t][f - 1].get(a) for a in ATTRS)]
                    swap = cambios[0] if cambios else lower
                fr = {f for f in st[t] if f >= swap}
                choque = fr & set(p_frames)
                if choque:
                    self.seguimiento.append(f"trayectoria {t}: el tramo P se superpone con P en {len(choque)} cuadros")
                    continue
                self.ops.append({"op": "reassign", "from_track": t, "to_track": P, "from_frame": swap,
                                 "to_frame": max(fr), "boxes": len(fr), **self.firma,
                                 "rationale": self.rationale(
                                     "R2", f"en la trayectoria {t}, las muestras desde {ms(fs[i0], self.fps)} son P "
                                     f"(antes: «{self.opt_text(q['id'], lab[fs[i0 - 1]]) if i0 else '—'}»); el "
                                     f"cambio de persona se ubica en {ms(swap, self.fps)}")})
                p_frames.update({f: st[t][f] for f in fr})
                self.alias[t] = P
        self._tramo_tapado(p_frames, P)
        self._oclusion_breve(p_frames, P)

    def _tramo_tapado(self, p_frames, P):
        q2 = next((q for q in self.s["preguntas"] if q.get("rol") == "tramo_tapado"), None)
        if not q2:
            return
        a = self.resp(q2["id"]).get("valor")
        nota = self.resp(q2["id"]).get("nota")
        if a != "tapado":
            if a in ("mixto",):
                self.seguimiento.append(f"tramo {q2['tramo_ms']}: respuesta «mixto» — {nota or 'sin nota'}")
            elif a is None:
                self.seguimiento.append(f"tramo {q2['tramo_ms']}: sin respuesta")
            return
        vals, notas = {}, []
        for q in self.s["preguntas"]:
            if q.get("rol") == "valor_tapado":
                r = self.resp(q["id"])
                if not r.get("valor"):
                    self.seguimiento.append(f"tramo tapado: falta {q['attr']}")
                    return
                vals[q["attr"]] = MAPA[r["valor"]]
                if r.get("nota"):
                    notas.append(f"{q['attr']}: «{r['nota']}»")
        lo = round(q2["tramo_ms"][0] * self.fps / 1000) - GAP_71
        hi = round(q2["tramo_ms"][1] * self.fps / 1000) + GAP_71
        self.tramo = (P, lo, hi, dict(vals), f"de {ms(lo, self.fps)} a {ms(hi, self.fps)} P sigue en cuadro, "
                      f"tapado («{self.opt_text(q2['id'], a)}»), y el revisor sabe su estado (casco "
                      f"{vals['has_helmet']}, chaleco {vals['has_vest']})" + (f"; {'; '.join(notas)}" if notas else ""))
        span = (min(p_frames), max(p_frames))
        hueco = [f for f in range(max(lo, span[0]), min(hi, span[1]) + 1) if f not in p_frames]
        for f0, f1 in runs(hueco):
            self.ops.append({"op": "fill", "track": P, "from_frame": f0, "to_frame": f1, "values": dict(vals),
                             **self.firma, "rationale": self.rationale(
                                 "R3", f"de {ms(f0, self.fps)} a {ms(f1, self.fps)} P sigue en cuadro, tapado "
                                 f"(«{self.opt_text(q2['id'], a)}»); casco {vals['has_helmet']}, chaleco "
                                 f"{vals['has_vest']}" + (f". Notas del revisor: {'; '.join(notas)}" if notas else "")
                                 + (f". Nota del tramo: «{nota}»" if nota else ""))})
            for f in range(f0, f1 + 1):
                p_frames[f] = dict(vals)

    def _oclusion_breve(self, p_frames, P):
        fs = sorted(p_frames)
        for a, b in zip(fs, fs[1:]):
            gap = b - a - 1
            if 0 < gap <= GAP_71 and all(p_frames[a].get(k) == p_frames[b].get(k) for k in ATTRS):
                vals = {k: p_frames[a][k] for k in ATTRS}
                self.ops.append({"op": "fill", "track": P, "from_frame": a + 1, "to_frame": b - 1, "values": vals,
                                 **self.firma, "rationale": self.rationale(
                                     "R4", f"hueco de {gap} cuadro(s) entre dos cajas de P con el mismo estado (casco "
                                     f"{vals['has_helmet']}, chaleco {vals['has_vest']}): oclusión breve, protocolo §7.1")})
                for f in range(a + 1, b):
                    p_frames[f] = dict(vals)

    # ---------------------------------------------------------------- atributos
    def deseados(self):
        """[(track_final, attr, {frame: valor}, q)] según R5."""
        out = []
        for q in self.s["preguntas"]:
            if q.get("rol") != "atributo":
                continue
            lab = {int(k): v for k, v in self.resp(q["id"]).items()}
            if not lab:
                self.seguimiento.append(f"{q['id']}: sin respuestas")
                continue
            fs = sorted(lab)
            vals, prev = {}, None
            for f in fs:
                v = lab[f]
                if v == "tapado":
                    v = prev
                else:
                    v = MAPA[v]
                vals[f] = v
                prev = v if v is not None else prev
            for f in fs:  # «tapado» en la primera muestra: toma la siguiente
                if vals[f] is None:
                    nxt = next((vals[g] for g in fs if g > f and vals[g] is not None), None)
                    vals[f] = nxt
            full = {}
            for f in range(fs[0], fs[-1] + 1):
                nxt = next(g for g in fs if g >= f)
                if vals[nxt] is not None:
                    full[f] = vals[nxt]
            t = self.alias.get(q["track"], q["track"])
            # qué opción definió cada cuadro (regla de la muestra siguiente)
            origen = {f: lab[next(g for g in fs if g >= f)] for f in full}
            out.append((t, q["attr"], full, q, len(fs), origen))
        return out

    def atributos(self, xml: Path, extender: bool):
        st, _, _ = tracks_state(xml)
        nuevos_fill = []
        self.attr_corr = []
        cubiertos = set()
        for t, attr, full, q, n, origen in self.deseados():
            vis = st.get(t, {})
            cambios = {f: (vis[f].get(attr), v) for f, v in full.items() if f in vis and vis[f].get(attr) != v}
            sin_caja = [f for f, v in full.items() if f not in vis and v in ("true", "false")]
            if extender and sin_caja:
                for f0, f1 in runs(sin_caja):
                    vals = {a: "unknown" for a in ATTRS}
                    vals[attr] = full[f0]
                    nuevos_fill.append({"op": "fill", "track": t, "from_frame": f0, "to_frame": f1, "occluded": False,
                                        "values": vals, **self.firma, "rationale": self.rationale(
                                            "R5", f"{q['id']}: la persona se ve ({attr}={full[f0]}) de {ms(f0, self.fps)} "
                                            f"a {ms(f1, self.fps)} y la trayectoria no tenía caja: se extiende")})
            grupos = []
            for f in sorted(cambios):
                prev, new = cambios[f]
                if grupos and grupos[-1]["to_frame"] == f - 1 and grupos[-1]["previous_value"] == prev \
                        and grupos[-1]["value"] == new:
                    grupos[-1]["to_frame"] = f
                else:
                    grupos.append({"track_id": t, "attr": attr, "from_frame": f, "to_frame": f,
                                   "previous_value": prev, "value": new})
            for g in grupos:
                g.update(self.firma)
                vistas = sorted({origen[f] for f in range(g["from_frame"], g["to_frame"] + 1)})
                txt_op = " / ".join(f"«{self.opt_text(q['id'], k)}»" for k in vistas)
                g["rationale"] = self.rationale(
                    "R5", f"{q['id']} «{q['enunciado'].strip()}»: {n} muestras de {ms(min(full), self.fps)} a "
                    f"{ms(max(full), self.fps)}; en {ms(g['from_frame'], self.fps)}–{ms(g['to_frame'], self.fps)} la "
                    f"respuesta fue {txt_op} → {g['attr']} = {g['value']}")
                self.attr_corr.append(g)
            cubiertos.update((t, attr, f) for f in full)
        if self.tramo:
            P, lo, hi, vals, txt = self.tramo
            for attr in ATTRS:
                if vals[attr] == "unknown":
                    continue
                fr = [f for f in range(lo, hi + 1) if f in st.get(P, {}) and st[P][f].get(attr) == "unknown"
                      and (P, attr, f) not in cubiertos]
                for f0, f1 in runs(fr):
                    self.attr_corr.append({
                        "track_id": P, "attr": attr, "from_frame": f0, "to_frame": f1, "previous_value": "unknown",
                        "value": vals[attr], **self.firma, "rationale": self.rationale(
                            "R3", txt + f"; en {ms(f0, self.fps)}–{ms(f1, self.fps)} la caja de P tenía {attr} "
                            "unknown (no se le veía): toma ese estado. No se pisa ningún valor explícito.")})
        return nuevos_fill


def episodios(gt):
    return [(e["condition_id"], e["start_ms"], e["end_ms"]) for e in gt["episodes"]]


def subumbral(gt):
    return [(e["condition_id"], e["start_ms"], e["end_ms"]) for e in gt.get("sub_threshold_events", [])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--respuestas", type=Path, help="default: <review>/respuestas.json")
    ap.add_argument("--salida", type=Path, help="default: la carpeta de la revisión")
    a = ap.parse_args(argv)
    spec = yaml.safe_load(a.spec.read_text())
    fps = int(spec.get("fps", 30))
    rdir = LAB / "review" / spec["revision"]
    casos_json = json.loads((rdir / "casos.json").read_text())
    R = json.loads((a.respuestas or rdir / "respuestas.json").read_text())
    odir = a.salida or rdir
    (odir / "correcciones").mkdir(parents=True, exist_ok=True)

    md = [f"# Propuesta de correcciones — {spec['revision']}", "",
          f"Revisor: **{R.get('revisor') or '(sin firma)'}** · terminado: {R.get('terminado', False)} · "
          f"guardado {R.get('guardado', '?')}", "",
          "Corrida en seco: nada de esto está aplicado al laboratorio. Cada clip se probó sobre una copia con "
          "las herramientas reales y se re-derivó el GT.", ""]
    total_pend = 0
    for sc in spec["casos"]:
        cj = next(c for c in casos_json["casos"] if c["id"] == sc["id"])
        caso = Caso(sc, cj, R, fps)
        pend = sum(len(q.get("items", [])) - len(caso.resp(q["id"].split(".")[1]))
                   if q["tipo"] != "opcion" else (0 if caso.resp(q["id"].split(".")[1]).get("valor") else 1)
                   for q in cj["preguntas"])
        total_pend += pend
        src_xml = LAB / "corrected" / f"{caso.clip}.xml"
        src_yaml = LAB / f"{caso.clip}.clip.yaml"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            caso.identidad(src_xml)

            def corrida(ops, attr_corr):
                x, y = td / "x.xml", td / "c.yaml"
                shutil.copy(src_xml, x)
                meta = yaml.safe_load(src_yaml.read_text()) or {}
                ann = dict(meta.get("annotation") or {})
                ann["identity_corrections"] = ops
                ann["attribute_corrections"] = list(ann.get("attribute_corrections") or []) + attr_corr
                meta["annotation"] = ann
                y.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False))
                ri = apply_identity(x, y)
                ra = apply_corrections(x, y) if ann["attribute_corrections"] else {"cajas_cambiadas": 0}
                return x, y, ri, ra

            x, y, _, _ = corrida(caso.ops, [])
            extra = caso.atributos(x, extender=True)
            if extra:
                caso.ops += extra
                x, y, _, _ = corrida(caso.ops, [])
                caso.atributos(x, extender=False)
            x, y, ri, ra = corrida(caso.ops, caso.attr_corr)
            gt_new = derive(x, y, LAB / "clips" / f"{caso.clip}.info.json", PATTERN_SET)
            gt_old = json.loads((BANK_GT / f"{caso.clip}.json").read_text())

        bloque = {}
        if caso.ops:
            bloque["identity_corrections"] = caso.ops
        if caso.attr_corr:
            bloque["attribute_corrections"] = caso.attr_corr
        (odir / "correcciones" / f"{caso.clip}.yaml").write_text(
            f"# Revisión dirigida 2026-10 — caso {caso.id} ({caso.clip}). Generado por convertir.py.\n"
            "# Agregar estas listas bajo `annotation:` en el clip.yaml (sin pisar lo que ya haya).\n"
            + (yaml.safe_dump(bloque, allow_unicode=True, sort_keys=False, width=110) if bloque else "# sin correcciones\n"))

        md += [f"## {caso.id} · {caso.clip} — {sc['titulo']}", ""]
        if pend:
            md.append(f"⚠ **{pend} respuesta(s) sin dar** en este caso.")
        for s in caso.seguimiento:
            md.append(f"- ⚠ seguimiento: {s}")
        nota = (R.get("notas") or {}).get(caso.id)
        if nota:
            md.append(f"- Nota del revisor: «{nota}»")
        md += ["", f"**Correcciones de identidad:** {len(caso.ops)} · **de atributo:** {len(caso.attr_corr)} "
                   f"({ra.get('cajas_cambiadas', 0)} cajas)", ""]
        for o in caso.ops:
            det = {k: v for k, v in o.items() if k not in ("decided_by", "decided_at", "rationale")}
            md.append(f"- `{json.dumps(det, ensure_ascii=False)}` — {o['rationale'].split(': ', 1)[1]}")
        for g in caso.attr_corr:
            md.append(f"- `{g['attr']}` trayectoria {g['track_id']} cuadros {g['from_frame']}–{g['to_frame']} "
                      f"({ms(g['from_frame'], fps)}–{ms(g['to_frame'], fps)}): {g['previous_value']} → {g['value']}")
        md += ["", f"| | Episodios | Sub-umbral |", "|---|---|---|",
               f"| GT vigente | {episodios(gt_old)} | {len(subumbral(gt_old))} |",
               f"| GT con las correcciones | {episodios(gt_new)} | {len(subumbral(gt_new))} |", ""]
        print(f"{caso.id} {caso.clip}: {len(caso.ops)} identidad · {len(caso.attr_corr)} atributo · "
              f"{episodios(gt_old)} → {episodios(gt_new)}" + (f" · ⚠ {len(caso.seguimiento)} seguimiento" if caso.seguimiento else ""))
    md.insert(4, f"**Respuestas sin dar en total: {total_pend}.**\n")
    (odir / "propuesta.md").write_text("\n".join(md) + "\n")
    print(f"escrito {odir / 'propuesta.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
