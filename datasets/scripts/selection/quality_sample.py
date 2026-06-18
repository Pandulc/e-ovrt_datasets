"""Muestrea N imágenes de un dataset y renderiza sus cajas para revisión de calidad.

Uso CLI:
    python datasets/scripts/selection/quality_sample.py --images <dir> --n 50 --seed 42 --out <dir>

La revisión es manual: se completa el checklist de calidad (ver metodología de selección).
"""
import argparse
import random
from pathlib import Path


def sample_image_ids(image_ids: list[str], n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    ids = sorted(image_ids)
    if n >= len(ids):
        return ids
    return sorted(rng.sample(ids, n))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--images", required=True, type=Path)
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    exts = {".jpg", ".jpeg", ".png"}
    ids = [f.name for f in args.images.iterdir() if f.suffix.lower() in exts]
    chosen = sample_image_ids(ids, args.n, args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "sampled.txt").write_text("\n".join(chosen))
    print(f"Muestreadas {len(chosen)}/{len(ids)} imágenes -> {args.out/'sampled.txt'}")


if __name__ == "__main__":
    main()
