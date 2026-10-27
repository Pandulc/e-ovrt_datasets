"""Prepara la vista de una revisión dirigida del GT: recortes, cuadros y videos por caso.

Lee la especificación (`datasets-videos/docs/<revision>.yaml`) y los XML corregidos
(`datasets-videos/corrected/<clip>.xml`), extrae los cuadros del clip con ffmpeg y
escribe en `datasets-videos/review/<revision>/` (gitignoreado: son imágenes de personas):

  casos.json          lo que la página muestra (SIN el valor anotado de ningún atributo)
  media/<caso>/...    recortes, cuadros ampliables y videos con las cajas rotuladas

Lo que la vista NO muestra, a propósito: los atributos anotados (`has_helmet`/`has_vest`),
las alertas del sistema, las métricas y las marcas de la ficha del rodaje. Las cajas sí se
muestran (con una letra por trayectoria), porque la identidad es parte de lo que se revisa.

Uso:
    python3 datasets/scripts/videogt/revision/preparar.py \
        --spec datasets-videos/docs/revision-dirigida-2026-10.yaml
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[4]
LAB = REPO / "datasets-videos"
CLIPS = REPO / "datasets/raw/clip_bench/clips"
PALETTE = ["#ff453a", "#32d74b", "#0a84ff", "#ffd60a", "#bf5af2", "#ff9f0a",
           "#64d2ff", "#ff375f", "#30d158", "#5e5ce6", "#ac8e68", "#ffffff"]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def parse_person_boxes(xml_path: Path) -> dict[int, dict[int, tuple]]:
    """{track_id: {frame: (xtl, ytl, xbr, ybr, occluded)}} — solo cajas visibles de `person`."""
    root = ET.parse(xml_path).getroot()
    out: dict[int, dict[int, tuple]] = {}
    for tr in root.findall("track"):
        if tr.get("label") != "person":
            continue
        boxes = {}
        for b in tr.findall("box"):
            if b.get("outside") == "1":
                continue
            boxes[int(b.get("frame"))] = tuple(float(b.get(k)) for k in ("xtl", "ytl", "xbr", "ybr")) + (
                b.get("occluded") == "1",)
        if boxes:
            out[int(tr.get("id"))] = boxes
    return out


def letters_for(tracks: dict[int, dict]) -> dict[int, str]:
    order = sorted(tracks, key=lambda t: (min(tracks[t]), t))
    return {t: LETTERS[i % len(LETTERS)] + ("" if i < len(LETTERS) else str(i // len(LETTERS))) for i, t in enumerate(order)}


def ms_to_f(ms: float, fps: int) -> int:
    return round(ms * fps / 1000)


def f_to_s(f: int, fps: int) -> str:
    return f"{f / fps:.2f}".replace(".", ",") + " s"


def contiguous(frames: list[int]) -> list[tuple[int, int]]:
    out = []
    for f in sorted(set(frames)):
        if out and f == out[-1][1] + 1:
            out[-1][1] = f
        else:
            out.append([f, f])
    return [tuple(x) for x in out]


def extract_frames(clip: str, frames: list[int], workdir: Path) -> dict[int, Path]:
    """Extrae EXACTAMENTE esos cuadros (índice n de ffmpeg = frame de CVAT)."""
    frames = sorted(set(frames))
    expr = "+".join(f"between(n\\,{a}\\,{b})" for a, b in contiguous(frames))
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(CLIPS / f"{clip}.mp4"), "-vf", f"select='{expr}'",
                    "-fps_mode", "passthrough", "-q:v", "2", str(workdir / "x_%06d.jpg")], check=True)
    files = sorted(workdir.glob("x_*.jpg"))
    if len(files) != len(frames):
        raise RuntimeError(f"{clip}: se pidieron {len(frames)} cuadros y ffmpeg devolvió {len(files)}")
    return dict(zip(frames, files))


def draw(im: Image.Image, tracks, letters, frame: int, thick: int | None = None, stamp: str | None = None,
         solo: int | None = None) -> Image.Image:
    im = im.copy()
    d = ImageDraw.Draw(im)
    f_lab = font(34)
    for tid, boxes in tracks.items():
        if frame not in boxes or (solo is not None and tid != solo):
            continue
        x0, y0, x1, y1, occ = boxes[frame]
        color = PALETTE[list(letters).index(tid) % len(PALETTE)]
        # El borde va POR FUERA de la caja: la caja llega justo al casco y un borde
        # dibujado encima podría taparlo.
        m = 16 if tid == thick else 6
        width = 10 if tid == thick else 4
        if tid == thick:
            d.rectangle([x0 - m - 6, y0 - m - 6, x1 + m + 6, y1 + m + 6], outline="white", width=4)
        d.rectangle([x0 - m, y0 - m, x1 + m, y1 + m], outline=color, width=width)
        lab = letters[tid]
        tw = d.textlength(lab, font=f_lab)
        ly = y0 - m - 50
        d.rectangle([x0 - m, max(0, ly), x0 - m + tw + 18, max(46, ly + 46)], fill=color)
        d.text((x0 - m + 9, max(0, ly) + 2), lab, fill="black", font=f_lab)
    if stamp:
        f_st = font(40)
        tw = d.textlength(stamp, font=f_st)
        d.rectangle([0, 0, tw + 30, 62], fill="black")
        d.text((15, 8), stamp, fill="white", font=f_st)
    return im


def crop(im: Image.Image, box: tuple, mode: str) -> Image.Image:
    x0, y0, x1, y1 = box[:4]
    w, h = x1 - x0, y1 - y0
    if mode == "cabeza":
        side = max(w * 1.25, h * 0.45)
        cx = (x0 + x1) / 2
        r = (cx - side / 2, y0 - 0.12 * h, cx + side / 2, y0 - 0.12 * h + side)
    else:  # persona
        r = (x0 - 0.08 * w, y0 - 0.06 * h, x1 + 0.08 * w, y1 + 0.03 * h)
    r = (max(0, r[0]), max(0, r[1]), min(im.width, r[2]), min(im.height, r[3]))
    return im.crop(tuple(int(v) for v in r))


def save(im: Image.Image, path: Path, max_w: int, max_h: int, quality: int = 84) -> str:
    im = im.copy()
    im.thumbnail((max_w, max_h))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=quality)
    return path.relative_to(path.parents[2]).as_posix()  # media/<caso>/<archivo>


def render_video(clip, tracks, letters, f0, f1, frames_png: dict[int, Path], out: Path, fps: int, work: Path):
    seq = work / f"v_{out.stem}"
    seq.mkdir()
    for i, f in enumerate(range(f0, f1 + 1)):
        im = draw(Image.open(frames_png[f]).convert("RGB"), tracks, letters, f, stamp=f_to_s(f, fps))
        im.thumbnail((960, 540))
        im.save(seq / f"{i:05d}.jpg", quality=88)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(seq / "%05d.jpg"),
                    "-vf", "scale=out_range=tv,format=yuv420p", "-c:v", "libx264", "-crf", "26",
                    "-preset", "veryfast", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(seq)


def fixed_region(tracks, f0: int, f1: int, frame_w: int = 1920, frame_h: int = 1080) -> tuple:
    """Encuadre FIJO para una pregunta de cuadro completo: la unión de todas las cajas de
    persona en [f0, f1], con margen. El mismo encuadre en todos los cuadros permite comparar
    de uno a otro (por ejemplo, ver a alguien entrar)."""
    xs0, ys0, xs1, ys1 = [], [], [], []
    for boxes in tracks.values():
        for f, b in boxes.items():
            if f0 <= f <= f1:
                xs0.append(b[0]); ys0.append(b[1]); xs1.append(b[2]); ys1.append(b[3])
    if not xs0:
        return (0, 0, frame_w, frame_h)
    x0, y0, x1, y1 = min(xs0), min(ys0), max(xs1), max(ys1)
    w, h = x1 - x0, y1 - y0
    x0, x1 = x0 - 0.30 * w - 120, x1 + 0.30 * w + 120
    y0, y1 = y0 - 0.12 * h - 60, y1 + 0.05 * h
    if x1 - x0 < 760:
        cx = (x0 + x1) / 2
        x0, x1 = cx - 380, cx + 380
    return (int(max(0, x0)), int(max(0, y0)), int(min(frame_w, x1)), int(min(frame_h, y1)))


def sample_frames(boxes: dict[int, tuple], n: int) -> list[int]:
    fs = sorted(boxes)
    if len(fs) <= n:
        return fs
    return sorted({fs[round(i * (len(fs) - 1) / (n - 1))] for i in range(n)})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--solo", help="ids de caso separados por coma (para regenerar uno)")
    a = ap.parse_args(argv)
    spec = yaml.safe_load(a.spec.read_text())
    fps = int(spec.get("fps", 30))
    out_dir = LAB / "review" / spec["revision"]
    media = out_dir / "media"
    media.mkdir(parents=True, exist_ok=True)
    solo = set(a.solo.split(",")) if a.solo else None

    casos_out = []
    for caso in spec["casos"]:
        clip = caso["clip"]
        tracks = parse_person_boxes(LAB / "corrected" / f"{clip}.xml")
        letters = letters_for(tracks)
        cdir = media / caso["id"]

        need: set[int] = set()
        for ref in caso.get("referencias", []):
            need.update(ref["frames"])
        for v in caso.get("videos", []):
            need.update(range(ms_to_f(v["desde_ms"], fps), ms_to_f(v["hasta_ms"], fps) + 1))
        for q in caso["preguntas"]:
            if q["tipo"] == "identidad":
                for t in q["tracks"]:
                    need.update(sample_frames(tracks[t], 5))
            elif q["tipo"] == "cuadros":
                need.update(range(ms_to_f(q["desde_ms"], fps), ms_to_f(q["hasta_ms"], fps) + 1, q["paso"]))

        caso_out = {"id": caso["id"], "clip": clip, "titulo": caso["titulo"], "contexto": caso["contexto"],
                    "referencias": [], "videos": [], "preguntas": []}
        if solo and caso["id"] not in solo:
            prev = json.loads((out_dir / "casos.json").read_text())
            casos_out.append(next(c for c in prev["casos"] if c["id"] == caso["id"]))
            continue
        if cdir.exists():
            shutil.rmtree(cdir)
        with tempfile.TemporaryDirectory(dir=out_dir) as td:
            work = Path(td)
            frames = extract_frames(clip, sorted(need), work)
            img = lambda f: Image.open(frames[f]).convert("RGB")  # noqa: E731

            for i, ref in enumerate(caso.get("referencias", [])):
                imgs = []
                for f in ref["frames"]:
                    imgs.append(save(crop(img(f), tracks[ref["track"]][f], "persona"),
                                     cdir / f"ref_{i}_{f}.jpg", 360, 420))
                caso_out["referencias"].append({"titulo": ref["titulo"], "imgs": imgs})

            for i, v in enumerate(caso.get("videos", [])):
                f0, f1 = ms_to_f(v["desde_ms"], fps), ms_to_f(v["hasta_ms"], fps)
                render_video(clip, tracks, letters, f0, f1, frames, cdir / f"video_{i}.mp4", fps, work)
                caso_out["videos"].append({"titulo": v["titulo"], "src": f"media/{caso['id']}/video_{i}.mp4"})

            for q in caso["preguntas"]:
                qo = {"id": f"{caso['id']}.{q['id']}", "tipo": q["tipo"], "enunciado": q["enunciado"].strip()}
                if q["tipo"] == "opcion":
                    qo["opciones"] = q["opciones"]
                    qo["nota"] = q.get("nota")
                elif q["tipo"] == "identidad":
                    qo["opciones"] = spec["opciones"]["identidad"]
                    qo["items"] = []
                    for t in q["tracks"]:
                        fs = sample_frames(tracks[t], 5)
                        mid = fs[len(fs) // 2]
                        crops = [save(crop(img(f), tracks[t][f], "persona"), cdir / f"id_{t}_{f}.jpg", 240, 320)
                                 for f in fs]
                        ctx = save(draw(img(mid), tracks, letters, mid, thick=t, stamp=f_to_s(mid, fps)),
                                   cdir / f"id_{t}_ctx.jpg", 1280, 720)
                        qo["items"].append({"id": str(t), "letra": letters[t],
                                            "rango": f"{f_to_s(min(tracks[t]), fps)} a {f_to_s(max(tracks[t]), fps)}",
                                            "cuadros": len(tracks[t]), "imgs": crops, "ctx": ctx})
                elif q["tipo"] == "cuadros":
                    t = q["track"]
                    qo["opciones"] = spec["opciones"][q["opciones"]]
                    qo["recorte"] = q["recorte"]
                    qo["items"] = []
                    qf0, qf1 = ms_to_f(q["desde_ms"], fps), ms_to_f(q["hasta_ms"], fps)
                    region = fixed_region(tracks, qf0, qf1)
                    for f in range(qf0, qf1 + 1, q["paso"]):
                        full = draw(img(f), tracks, letters, f, thick=t, stamp=f_to_s(f, fps))
                        full_rel = save(full, cdir / f"{q['id']}_{f}_full.jpg", 1280, 720)
                        if q["recorte"] == "cuadro" or f not in tracks[t]:
                            thumb = save(full.crop(region), cdir / f"{q['id']}_{f}_th.jpg", 360, 300)
                        else:
                            mode = "cabeza" if q["recorte"] == "cabeza" else "persona"
                            thumb = save(crop(draw(img(f), tracks, letters, f, thick=t, solo=t), tracks[t][f], mode),
                                         cdir / f"{q['id']}_{f}_th.jpg", 220 if mode == "cabeza" else 200,
                                         220 if mode == "cabeza" else 340)
                        qo["items"].append({"id": str(f), "t": f_to_s(f, fps), "thumb": thumb, "full": full_rel,
                                            "caja": f in tracks[t]})
                caso_out["preguntas"].append(qo)
        casos_out.append(caso_out)
        n_items = sum(len(q.get("items", [])) or 1 for q in caso_out["preguntas"])
        print(f"{caso['id']} {clip}: {len(need)} cuadros extraídos · {n_items} respuestas a dar")

    (out_dir / "casos.json").write_text(json.dumps({
        "revision": spec["revision"], "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fps": fps, "casos": casos_out}, ensure_ascii=False, indent=1))
    print(f"escrito {out_dir / 'casos.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
