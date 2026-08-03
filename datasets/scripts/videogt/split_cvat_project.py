"""Divide un export CVAT a nivel PROYECTO en un XML por task (etapa 2b).

CVAT exporta un proyecto como un único `annotations.xml` donde los tracks se
distinguen por el atributo `task_id`, pero los frames viven en un espacio
**global y continuo**: la task N empieza donde termina la N-1. El resto del
laboratorio (`cvat_xml.parse_cvat_video_xml`, `derive_clip_gt`) asume el
contrato de un export a nivel task: frames 0-based respecto del clip.

Sin rebase el fallo es SILENCIOSO y total: todas las cajas caen fuera de
`[0, n_frames-1]`, `attribute_states` devuelve None en todo el timeline y cada
clip sale `negative: true`. El guard C2 de `derive_clip_gt` no lo atrapa —los
tracks con label 'person' existen— así que el banco se llenaría de negativos
falsos y toda violación real se contaría como falso positivo del modelo.

El offset de cada task es la suma acumulada de los `<size>` anteriores en orden
de documento. El invariante se verifica caja por caja antes de rebasar: si
alguna cae fuera de la ventana de su task, el modelo no aplica y se corta.
"""
from __future__ import annotations

import argparse
import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path

_TASK_META_FIELDS = ("id", "name", "size", "mode", "overlap",
                     "start_frame", "stop_frame", "original_size", "source")


def _project_tasks(root: ET.Element) -> list[ET.Element]:
    """Tasks del export de proyecto, en orden de documento."""
    tasks_el = root.find("./meta/project/tasks")
    if tasks_el is None:
        raise ValueError(
            "el XML no es un export de PROYECTO (falta <meta><project><tasks>). "
            "Un export a nivel task ya viene con frames 0-based y se consume "
            "directo con derive_clip_gt.py — no hay nada que dividir."
        )
    tasks = tasks_el.findall("task")
    if not tasks:
        raise ValueError("el export de proyecto no declara ninguna task")
    return tasks


def _task_meta(task_el: ET.Element, size: int) -> ET.Element:
    """`<meta><task>…` con el contrato que espera el parser (size local)."""
    meta = ET.Element("meta")
    task = ET.SubElement(meta, "task")
    for field in _TASK_META_FIELDS:
        src = task_el.find(field)
        if src is None:
            continue
        dst = ET.SubElement(task, field)
        if len(src):
            dst.extend(copy.deepcopy(list(src)))
        else:
            dst.text = src.text
    # El clip dividido siempre arranca en 0: lo que el resto del laboratorio
    # asume y lo que hace válido el guard I2 contra n_frames del .info.json.
    for field, value in (("size", size), ("start_frame", 0), ("stop_frame", size - 1)):
        el = task.find(field)
        if el is None:
            el = ET.SubElement(task, field)
        el.text = str(value)
    return meta


def split_project_export(xml_path: str | Path, only: set[str] | None = None,
                         match: str | None = None) -> list[dict]:
    """Export de proyecto → una entrada por task, con los frames rebaseados.

    Devuelve `[{'task_id', 'name', 'size', 'offset', 'tracks', 'boxes',
    'xml'}, …]` en orden de documento. `only` filtra por nombre exacto (y
    falla si alguno no existe); `match` filtra por regex sobre el nombre.
    """
    root = ET.parse(str(xml_path)).getroot()
    tasks = _project_tasks(root)

    offsets, sizes, elements, order = {}, {}, {}, []
    acc = 0
    for task_el in tasks:
        tid = (task_el.findtext("id") or "").strip()
        name = (task_el.findtext("name") or "").strip()
        size = int((task_el.findtext("size") or "0").strip())
        offsets[tid], sizes[tid], elements[tid] = acc, size, task_el
        order.append((tid, name))
        acc += size

    names = {name for _, name in order}
    if only is not None:
        missing = sorted(only - names)
        if missing:
            raise ValueError(
                f"estos nombres no existen en el export: {', '.join(missing)} "
                f"(el export trae {len(names)} tasks)"
            )
    pattern = re.compile(match) if match else None

    tracks_by_task: dict[str, list[ET.Element]] = {tid: [] for tid, _ in order}
    for track in root.findall("track"):
        tid = track.get("task_id")
        if tid not in tracks_by_task:
            raise ValueError(
                f"track id={track.get('id')} referencia task_id={tid!r}, que no "
                "está declarado en <meta><project><tasks>"
            )
        tracks_by_task[tid].append(track)

    out = []
    for tid, name in order:
        if only is not None and name not in only:
            continue
        if pattern is not None and not pattern.search(name):
            continue
        offset, size = offsets[tid], sizes[tid]
        lo, hi = offset, offset + size - 1

        annotations = ET.Element("annotations")
        version = ET.SubElement(annotations, "version")
        version.text = (root.findtext("version") or "1.1").strip()
        annotations.append(_task_meta(elements[tid], size))

        n_boxes = 0
        for track in tracks_by_task[tid]:
            clone = copy.deepcopy(track)
            for shape in clone:
                raw = shape.get("frame")
                if raw is None:
                    continue
                frame = int(raw)
                if not lo <= frame <= hi:
                    raise ValueError(
                        f"task {name!r} (id={tid}): frame {frame} fuera de la "
                        f"ventana [{lo}, {hi}] que le corresponde por el offset "
                        f"acumulado. El modelo de numeración global no aplica a "
                        f"este export — revisá la versión de CVAT antes de rebasar."
                    )
                shape.set("frame", str(frame - offset))
                n_boxes += 1
            annotations.append(clone)

        ET.indent(annotations, space="  ")
        out.append({
            "task_id": tid,
            "name": name,
            "size": size,
            "offset": offset,
            "tracks": len(tracks_by_task[tid]),
            "boxes": n_boxes,
            "xml": '<?xml version="1.0" encoding="utf-8"?>\n'
                   + ET.tostring(annotations, encoding="unicode") + "\n",
        })
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", required=True, help="annotations.xml del export de proyecto")
    parser.add_argument("--out-dir", required=True, help="destino de los <task_name>.xml")
    parser.add_argument("--only", default="", help="lista de nombres separados por coma")
    parser.add_argument("--match", default=None, help="regex sobre el nombre de la task")
    parser.add_argument("--dry-run", action="store_true", help="no escribe, solo lista")
    args = parser.parse_args(argv)

    only = {n.strip() for n in args.only.split(",") if n.strip()} or None
    try:
        parts = split_project_export(args.xml, only=only, match=args.match)
    except ValueError as e:
        parser.error(str(e))

    out_dir = Path(args.out_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    for p in parts:
        dest = out_dir / f"{p['name']}.xml"
        if not args.dry_run:
            dest.write_text(p["xml"])
        print(f"  {p['name']:14} offset={p['offset']:6}  size={p['size']:5}  "
              f"tracks={p['tracks']:4}  cajas={p['boxes']:6}  → {dest}")
    verb = "listadas" if args.dry_run else "escritas"
    print(f"✓ {len(parts)} tasks {verb} en {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
