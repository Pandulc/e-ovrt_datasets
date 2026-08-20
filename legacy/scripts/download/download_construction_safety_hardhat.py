#!/usr/bin/env python3
# DEPRECATED (2026-06-17): construction_safety_hardhat discarded — invalid Kaggle URL, never downloaded.
"""Downloads construction-safety-image-classification-system from Kaggle (CC0).

Supports both Kaggle auth formats:
  - New: KAGGLE_API_TOKEN env var or ~/.kaggle/access_token  (Bearer token, KGAT_...)
  - Old: ~/.kaggle/kaggle.json with {username, key}           (Basic auth)

Usage: python3 download_construction_safety_hardhat.py
"""
import hashlib
import os
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNER = "muhammetzualli"
DATASET = "construction-safety-image-classification-system"
OUT = ROOT / "datasets" / "raw" / "construction_safety_hardhat" / f"{DATASET}.zip"
URL = f"https://www.kaggle.com/api/v1/datasets/download/{OWNER}/{DATASET}"


def _auth_header() -> str:
    # 1. Env var (new format)
    token = os.environ.get("KAGGLE_API_TOKEN", "")
    if token:
        return f"Bearer {token}"

    # 2. ~/.kaggle/access_token (new format)
    access_token_path = Path.home() / ".kaggle" / "access_token"
    if access_token_path.exists():
        token = access_token_path.read_text().strip()
        return f"Bearer {token}"

    # 3. ~/.kaggle/kaggle.json (old format)
    import base64, json
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        cred = json.loads(kaggle_json.read_text())
        token = base64.b64encode(f"{cred['username']}:{cred['key']}".encode()).decode()
        return f"Basic {token}"

    print("No Kaggle credentials found. Try one of:", file=sys.stderr)
    print("  export KAGGLE_API_TOKEN=KGAT_...", file=sys.stderr)
    print("  or save token to ~/.kaggle/access_token", file=sys.stderr)
    sys.exit(2)


if OUT.exists():
    print(f"File already exists: {OUT}")
    sys.exit(0)

OUT.parent.mkdir(parents=True, exist_ok=True)
req = urllib.request.Request(URL, headers={
    "Authorization": _auth_header(),
    "User-Agent": "e-ovrt-dataset-downloader/1.0",
})
tmp = OUT.with_suffix(".zip.part")
try:
    with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as f:
        total = 0
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total % (100 * 1024 * 1024) < 1024 * 1024:
                print(f"downloaded_mb: {total // (1024 * 1024)}")
    tmp.replace(OUT)
    print(f"wrote: {OUT}")
except urllib.error.HTTPError as e:
    print(f"http_error: {e.code}", file=sys.stderr)
    print(e.read(500).decode(errors="replace"), file=sys.stderr)
    sys.exit(1)

sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
print(f"sha256: {sha}  {OUT.name}")

extract_dir = OUT.parent
with zipfile.ZipFile(OUT) as z:
    z.extractall(extract_dir)
print(f"Extracted into: {extract_dir}")

imgs = list(extract_dir.rglob("*.jpg")) + list(extract_dir.rglob("*.jpeg")) + list(extract_dir.rglob("*.png"))
print(f"Image count: {len(imgs)}")

labels = list(extract_dir.rglob("*.txt"))
print(f"YOLO label count: {len(labels)}")
if not labels:
    print("WARNING: no .txt label files found — dataset may be classification-only (no bounding boxes).")
    print("If so, this dataset cannot be used for YOLO detection conversion.")
else:
    dirs = sorted({p.parent.name for p in labels})
    print(f"Label subdirs (first 5): {dirs[:5]}")
