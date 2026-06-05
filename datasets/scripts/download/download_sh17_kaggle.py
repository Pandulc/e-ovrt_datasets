#!/usr/bin/env python3
from pathlib import Path
import base64
import json
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
CRED_PATH = Path.home() / ".kaggle" / "kaggle.json"
OUT = ROOT / "datasets" / "raw" / "sh17" / "sh17-kaggle.zip"
URL = "https://www.kaggle.com/api/v1/datasets/download/mugheesahmad/sh17-dataset-for-ppe-detection"

if not CRED_PATH.exists():
    print(f"Missing Kaggle credentials: {CRED_PATH}", file=sys.stderr)
    sys.exit(2)

if OUT.exists():
    print(f"File already exists: {OUT}")
    sys.exit(0)

cred = json.loads(CRED_PATH.read_text())
token = base64.b64encode(f"{cred['username']}:{cred['key']}".encode()).decode()
req = urllib.request.Request(URL, headers={
    "Authorization": f"Basic {token}",
    "User-Agent": "codex-dataset-downloader/1.0",
})
OUT.parent.mkdir(parents=True, exist_ok=True)
tmp = OUT.with_suffix(".zip.part")
try:
    with urllib.request.urlopen(req, timeout=60) as r, tmp.open("wb") as f:
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
