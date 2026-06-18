"""Verifica que TRAIN y BENCH no compartan imágenes/escenas (spec §8.5, G5)."""
import argparse
from pathlib import Path


def find_leaks(train_ids: set[str], bench_ids: set[str]) -> set[str]:
    return train_ids & bench_ids


def _ids(d: Path) -> set[str]:
    exts = {".jpg", ".jpeg", ".png"}
    return {f.stem for f in d.rglob("*") if f.suffix.lower() in exts}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--train", required=True, type=Path)
    p.add_argument("--bench", required=True, type=Path)
    args = p.parse_args()
    leaks = find_leaks(_ids(args.train), _ids(args.bench))
    if leaks:
        raise SystemExit(f"FUGA: {len(leaks)} ids compartidos: {sorted(leaks)[:10]}")
    print("Sin fuga TRAIN<->BENCH")


if __name__ == "__main__":
    main()
