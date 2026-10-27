"""Aplica CORRECCIONES DE IDENTIDAD declaradas en `clip.yaml` sobre el XML corregido.

Hermano de `apply_attribute_corrections.py`. Aquel corrige el VALOR de un atributo de una
persona; este corrige QUIÉN es cada caja. Hace falta porque `derive_clip_gt` umbrala la
persistencia POR TRAYECTORIA (regla C1): si la anotación parte a una persona en varias
trayectorias —típico cuando otra persona se le cruza adelante, o cuando dos se cruzan y
las trayectorias se intercambian— ninguna sostiene sola los 4 s y el episodio se parte o
desaparece, aunque el estado de la persona no haya cambiado. El protocolo del anotador
(`docs/etiquetado-cvat.md` §7.1) pide exactamente lo contrario: ante una oclusión, mantener
la trayectoria y marcar `occluded`.

**Dónde vive la decisión.** En `clip.yaml`, bajo `annotation.identity_corrections` — nunca
en el XML, que es un artefacto regenerable (mismo criterio que las otras dos herramientas).

Esquema. Campos comunes, todos obligatorios: `op`, `decided_by`, `decided_at`, `rationale`.

    annotation:
      identity_corrections:
        - op: reassign        # las cajas VISIBLES de from_track en [from_frame, to_frame]
          from_track: 603     #   pasan a to_track (la misma persona)
          to_track: 607
          from_frame: 396
          to_frame: 807
          boxes: 412          # guard: cuántas cajas visibles se mueven
        - op: fill            # la persona sigue en cuadro, tapada: cajas `occluded=1` con el
          track: 607          #   estado que decidió el revisor (geometría interpolada; no la
          from_frame: 196     #   usa ninguna métrica, §7.4)
          to_frame: 395
          values: {has_helmet: "false", has_vest: "true"}
          occluded: true      # opcional (default true). false = la persona se ve pero la caja
                              #   empezaba tarde (p.ej. al entrar a cuadro): se extiende
        - op: close           # cierra una trayectoria que quedó «viva» hasta el final del clip
          track: 629          #   (CVAT: una caja sin cierre explícito vale hasta el último cuadro)
        - op: drop            # elimina una trayectoria que no corresponde a ninguna persona
          track: 630
          boxes: 1

Las operaciones se aplican en el orden declarado. Después, cada trayectoria tocada se
NORMALIZA: cada tramo de cajas visibles termina con una caja `outside=1` en el cuadro
siguiente (si no es el último del clip), y se descartan las cajas `outside=1` que quedaron
dentro de un tramo visible. Sin eso, un tramo movido o recortado quedaría vivo hasta el final.

Guards: los conteos declarados (`boxes`) tienen que coincidir; `fill` no pisa cajas visibles
que no sean suyas; toda operación es idempotente (re-correr la cadena no cambia nada).

Flujo:  split_cvat_project → apply_adjudications → apply_identity_corrections
        → apply_attribute_corrections → derive_clip_gt

Uso:
    python3 datasets/scripts/videogt/apply_identity_corrections.py \\
        --xml datasets-videos/corrected/<clip>.xml \\
        --clip-yaml datasets-videos/<clip>.clip.yaml [--out <xml>] [--check]
"""
from __future__ import annotations

import argparse
import copy
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

COMUNES = ("op", "decided_by", "decided_at", "rationale")
POR_OP = {
    "reassign": ("from_track", "to_track", "from_frame", "to_frame", "boxes"),
    "fill": ("track", "from_frame", "to_frame", "values"),
    "close": ("track",),
    "drop": ("track", "boxes"),
}
ATRIBUTOS = ("has_helmet", "has_vest")
VALORES = {"true", "false", "unknown"}


class IdentityError(Exception):
    """Corrección mal declarada, conteo que no coincide o conflicto con el XML."""


def _validar(c: dict, i: int) -> None:
    op = c.get("op")
    if op not in POR_OP:
        raise IdentityError(f"identity_corrections[{i}]: op {op!r} inválida (esperado {sorted(POR_OP)})")
    faltan = [k for k in COMUNES + POR_OP[op] if k not in c or c[k] in ("", None)]
    if faltan:
        raise IdentityError(f"identity_corrections[{i}] ({op}): faltan campos obligatorios: {', '.join(faltan)}")
    if op in ("reassign", "fill") and int(c["from_frame"]) > int(c["to_frame"]):
        raise IdentityError(f"identity_corrections[{i}] ({op}): from_frame > to_frame")
    if op == "reassign" and int(c["from_track"]) == int(c["to_track"]):
        raise IdentityError(f"identity_corrections[{i}]: from_track == to_track")
    if op == "fill":
        vals = c["values"]
        if not isinstance(vals, dict) or set(vals) != set(ATRIBUTOS) or \
                any(str(v).lower() not in VALORES for v in vals.values()):
            raise IdentityError(f"identity_corrections[{i}] (fill): `values` tiene que declarar "
                                f"{list(ATRIBUTOS)} con valores en {sorted(VALORES)}")


def _tracks(root) -> dict[int, ET.Element]:
    return {int(t.get("id")): t for t in root.findall("track")}


def _boxes(track: ET.Element) -> list[ET.Element]:
    return track.findall("box")


def _visible(track: ET.Element, f0: int = -1, f1: int = 10 ** 9) -> list[ET.Element]:
    return [b for b in _boxes(track) if b.get("outside") == "0" and f0 <= int(b.get("frame")) <= f1]


def _stop_frame(root) -> int | None:
    for xp in ("./meta/task/size", "./meta/job/size"):
        el = root.find(xp)
        if el is not None and (el.text or "").strip().isdigit():
            return int(el.text.strip()) - 1
    return None


def _attr(box: ET.Element, name: str) -> str | None:
    for a in box.findall("attribute"):
        if a.get("name") == name:
            return (a.text or "").strip().lower()
    return None


def _set_attr(box: ET.Element, name: str, value: str) -> None:
    for a in box.findall("attribute"):
        if a.get("name") == name:
            a.text = value
            return
    ET.SubElement(box, "attribute", {"name": name}).text = value


def _sort_track(track: ET.Element) -> None:
    boxes = sorted(_boxes(track), key=lambda b: (int(b.get("frame")), b.get("outside") == "0"))
    for b in _boxes(track):
        track.remove(b)
    for b in boxes:
        track.append(b)


def _normalize(track: ET.Element, stop_frame: int | None) -> None:
    """Cada tramo visible termina en una caja outside=1; ninguna outside=1 dentro de un tramo."""
    vis = {int(b.get("frame")): b for b in _boxes(track) if b.get("outside") == "0"}
    for b in [b for b in _boxes(track) if b.get("outside") == "1"]:
        if int(b.get("frame")) in vis:
            track.remove(b)
    outs = {int(b.get("frame")) for b in _boxes(track) if b.get("outside") == "1"}
    for f in sorted(vis):
        nxt = f + 1
        if nxt in vis or (stop_frame is not None and nxt > stop_frame) or nxt in outs:
            continue
        closing = copy.deepcopy(vis[f])
        closing.set("frame", str(nxt))
        closing.set("outside", "1")
        closing.set("keyframe", "1")
        closing.set("occluded", "0")
        track.append(closing)
    _sort_track(track)


def _interp(a: ET.Element | None, b: ET.Element | None, f: int) -> dict:
    keys = ("xtl", "ytl", "xbr", "ybr")
    if a is None and b is None:
        raise IdentityError("fill: la trayectoria no tiene ninguna caja visible para tomar la geometría")
    if a is None or b is None:
        src = a if a is not None else b
        return {k: src.get(k) for k in keys}
    fa, fb = int(a.get("frame")), int(b.get("frame"))
    w = 0.0 if fb == fa else (f - fa) / (fb - fa)
    return {k: f"{float(a.get(k)) + w * (float(b.get(k)) - float(a.get(k))):.2f}" for k in keys}


def apply_identity(xml_path, clip_yaml_path, out_path=None) -> dict:
    meta = yaml.safe_load(Path(clip_yaml_path).read_text()) or {}
    ops = (meta.get("annotation") or {}).get("identity_corrections") or []
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    stop = _stop_frame(root)
    resumen = {"correcciones": len(ops), "aplicadas": 0, "ya_estaban": 0, "detalle": []}
    tocadas: set[int] = set()

    for i, c in enumerate(ops):
        _validar(c, i)
        op, tr = c["op"], _tracks(root)
        estado = None
        if op == "reassign":
            src_id, dst_id = int(c["from_track"]), int(c["to_track"])
            f0, f1, n = int(c["from_frame"]), int(c["to_frame"]), int(c["boxes"])
            if dst_id not in tr:
                raise IdentityError(f"identity_corrections[{i}] (reassign): no existe to_track={dst_id}")
            mover = _visible(tr[src_id], f0, f1) if src_id in tr else []
            ya = _visible(tr[dst_id], f0, f1)
            # «>=»: una operación posterior puede haber sumado cajas al destino dentro del mismo
            # rango (p.ej. una caja suelta que llena un hueco de la trayectoria ya reasignada).
            if not mover and len(ya) >= n:
                estado = "ya_estaban"
            else:
                if len(mover) != n:
                    raise IdentityError(
                        f"identity_corrections[{i}] (reassign {src_id}→{dst_id} [{f0}..{f1}]): se declararon "
                        f"{n} cajas visibles y hay {len(mover)}. El XML cambió por debajo; revisá antes de mover.")
                choque = {int(b.get('frame')) for b in ya} & {int(b.get('frame')) for b in mover}
                if choque:
                    raise IdentityError(
                        f"identity_corrections[{i}] (reassign): to_track={dst_id} ya tiene cajas visibles en "
                        f"{len(choque)} de esos cuadros (p.ej. f{min(choque)}): dos cajas de la misma persona.")
                frames_mov = {int(b.get("frame")) for b in mover}
                for b in [b for b in _boxes(tr[dst_id]) if b.get("outside") == "1"
                          and int(b.get("frame")) in frames_mov]:
                    tr[dst_id].remove(b)
                for b in mover:
                    tr[src_id].remove(b)
                    tr[dst_id].append(b)
                if not _visible(tr[src_id]):
                    root.remove(tr[src_id])
                else:
                    tocadas.add(src_id)
                tocadas.add(dst_id)
                estado = "aplicada"
        elif op == "fill":
            tid, f0, f1 = int(c["track"]), int(c["from_frame"]), int(c["to_frame"])
            vals = {k: str(v).lower() for k, v in c["values"].items()}
            occ = "1" if c.get("occluded", True) else "0"
            if tid not in tr:
                raise IdentityError(f"identity_corrections[{i}] (fill): no existe track={tid}")
            en_rango = _visible(tr[tid], f0, f1)
            propias = [b for b in en_rango if b.get("occluded") == occ
                       and all(_attr(b, k) == v for k, v in vals.items())]
            if len(propias) == f1 - f0 + 1:
                estado = "ya_estaban"
            elif en_rango:
                raise IdentityError(
                    f"identity_corrections[{i}] (fill {tid} [{f0}..{f1}]): la trayectoria ya tiene "
                    f"{len(en_rango)} caja(s) visibles en el rango (p.ej. f{en_rango[0].get('frame')}). "
                    f"`fill` solo rellena huecos: revisá el rango o reasigná antes.")
            else:
                antes = [b for b in _visible(tr[tid]) if int(b.get("frame")) < f0]
                despues = [b for b in _visible(tr[tid]) if int(b.get("frame")) > f1]
                a = max(antes, key=lambda b: int(b.get("frame")), default=None)
                b2 = min(despues, key=lambda b: int(b.get("frame")), default=None)
                plantilla = a if a is not None else b2
                if plantilla is None:
                    raise IdentityError(f"identity_corrections[{i}] (fill): track={tid} no tiene cajas visibles")
                for b in [b for b in _boxes(tr[tid]) if b.get("outside") == "1" and f0 <= int(b.get("frame")) <= f1]:
                    tr[tid].remove(b)
                for f in range(f0, f1 + 1):
                    nb = copy.deepcopy(plantilla)
                    nb.set("frame", str(f))
                    nb.set("outside", "0")
                    nb.set("occluded", occ)
                    nb.set("keyframe", "1" if f == f0 else "0")
                    for k, v in _interp(a, b2, f).items():
                        nb.set(k, v)
                    for k, v in vals.items():
                        _set_attr(nb, k, v)
                    tr[tid].append(nb)
                tocadas.add(tid)
                estado = "aplicada"
        elif op == "close":
            tid = int(c["track"])
            if tid not in tr:
                raise IdentityError(f"identity_corrections[{i}] (close): no existe track={tid}")
            vis = _visible(tr[tid])
            if not vis:
                raise IdentityError(f"identity_corrections[{i}] (close): track={tid} no tiene cajas visibles")
            last = max(int(b.get("frame")) for b in vis)
            cerrada = (stop is not None and last >= stop) or any(
                b.get("outside") == "1" and int(b.get("frame")) == last + 1 for b in _boxes(tr[tid]))
            if cerrada:
                estado = "ya_estaban"
            else:
                tocadas.add(tid)
                estado = "aplicada"
        elif op == "drop":
            tid, n = int(c["track"]), int(c["boxes"])
            if tid not in tr:
                estado = "ya_estaban"
            else:
                vis = _visible(tr[tid])
                if len(vis) != n:
                    raise IdentityError(f"identity_corrections[{i}] (drop {tid}): se declararon {n} cajas "
                                        f"visibles y hay {len(vis)}.")
                root.remove(tr[tid])
                tocadas.discard(tid)
                estado = "aplicada"
        resumen["aplicadas" if estado == "aplicada" else "ya_estaban"] += 1
        resumen["detalle"].append({"op": op, "estado": estado, "decided_by": c["decided_by"],
                                   **{k: c[k] for k in POR_OP[op] if k != "values"}})

    tr = _tracks(root)
    for tid in tocadas:
        if tid in tr:
            _normalize(tr[tid], stop)
    if ops:
        tree.write(str(Path(out_path or xml_path)), encoding="utf-8", xml_declaration=True)
    return resumen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml", required=True)
    ap.add_argument("--clip-yaml", required=True)
    ap.add_argument("--out", default=None, help="default: in-place sobre --xml")
    ap.add_argument("--check", action="store_true",
                    help="NO escribe: verifica que las correcciones YA estén aplicadas (sale 1 si falta alguna)")
    a = ap.parse_args(argv)
    try:
        r = apply_identity(a.xml, a.clip_yaml, os.devnull if a.check else a.out)
    except IdentityError as e:
        if a.check:
            print(f"✗ {a.xml}: {e}")
            return 1
        ap.error(str(e))
    if not r["correcciones"]:
        print("sin identity_corrections declaradas — nada que hacer")
        return 0
    for d in r["detalle"]:
        print(f"  [{d['estado']}] {d['op']} " + " ".join(f"{k}={v}" for k, v in d.items()
                                                        if k not in ('op', 'estado', 'decided_by')))
    if a.check:
        if r["aplicadas"]:
            print(f"✗ {r['aplicadas']} corrección(es) de identidad NO aplicada(s) en {a.xml}")
            return 1
        print(f"✓ las {r['correcciones']} corrección(es) de identidad están aplicadas")
        return 0
    print(f"✓ {r['aplicadas']} aplicada(s), {r['ya_estaban']} ya estaban")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
