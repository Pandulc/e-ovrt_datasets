#!/usr/bin/env bash
# Downloads ppe-dataset-for-workplace-safety from Roboflow Universe (CC BY 4.0).
# Requires: ROBOFLOW_API_KEY env var, curl, python3 (for JSON parsing), unzip.
# Usage: ROBOFLOW_API_KEY=<key> bash download_ppe_siabar.sh [version]
set -euo pipefail

WORKSPACE="siabar"
PROJECT="ppe-dataset-for-workplace-safety"
VERSION="${1:-1}"
FORMAT="yolov8"

: "${ROBOFLOW_API_KEY:?Set ROBOFLOW_API_KEY before running this script}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/ppe_siabar"
ZIP_PATH="${RAW_DIR}/${PROJECT}-v${VERSION}-${FORMAT}.zip"
TMP_JSON="$(mktemp)"

mkdir -p "${RAW_DIR}"

if [[ -f "${ZIP_PATH}" ]]; then
  echo "Archive already exists: ${ZIP_PATH}"
else
  echo "Requesting export link from Roboflow API..."
  curl -sf "https://api.roboflow.com/${WORKSPACE}/${PROJECT}/${VERSION}/${FORMAT}?api_key=${ROBOFLOW_API_KEY}" \
    -o "${TMP_JSON}"
  DOWNLOAD_LINK=$(python3 -c "import json,sys; print(json.load(open('${TMP_JSON}'))['export']['link'])")
  rm -f "${TMP_JSON}"
  echo "Downloading..."
  curl -L "${DOWNLOAD_LINK}" -o "${ZIP_PATH}"
fi

echo "SHA256:"; sha256sum "${ZIP_PATH}"

if command -v unzip >/dev/null 2>&1; then
  unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
  echo "Extracted into: ${RAW_DIR}"
else
  echo "unzip not available; archive at ${ZIP_PATH}"
fi

echo "Image count:"; find "${RAW_DIR}" -type f \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' \) | wc -l

# Print class list from data.yaml so you can verify it matches DatasetConfig.classes in convert_datasets.py
DATA_YAML=$(find "${RAW_DIR}" -maxdepth 2 -name "data.yaml" | head -1)
if [[ -n "${DATA_YAML}" ]]; then
  echo ""
  echo "Classes in ${DATA_YAML} (verify order matches DatasetConfig.classes in convert_datasets.py):"
  python3 -c "
import sys
try:
    import yaml
    with open('${DATA_YAML}') as f:
        d = yaml.safe_load(f)
    names = d.get('names', [])
    if isinstance(names, dict):
        names = [names[i] for i in sorted(names)]
    for i, n in enumerate(names): print(f'  [{i}] {n}')
except ImportError:
    import re, pathlib
    txt = pathlib.Path('${DATA_YAML}').read_text()
    for line in txt.splitlines():
        if re.match(r'\s*[-\d]', line): print(' ', line)
"
fi
