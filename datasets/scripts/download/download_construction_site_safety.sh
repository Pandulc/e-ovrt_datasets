#!/usr/bin/env bash
# Downloads construction-site-safety from Roboflow Universe (CC BY 4.0).
# Requires: ROBOFLOW_API_KEY env var, curl, python3 (for JSON parsing), unzip.
# Usage: ROBOFLOW_API_KEY=<key> bash download_construction_site_safety.sh [version]
#
# ✎ 2026-10-27: la versión por defecto es la 27, la que se descargó el 2026-06-18 y de la que
# salen las imágenes de obra de bench_v3 (download_log.md). El default anterior (3) no existe en
# Roboflow. Verificar después, imagen por imagen:
#   sha256sum -c datasets/registry/imagenes_obra_y_mocs.sha256   (desde la raíz del repo)
set -euo pipefail

WORKSPACE="roboflow-universe-projects"
PROJECT="construction-site-safety"
VERSION="${1:-27}"
FORMAT="yolov8"
# sha256 del zip de la v27 descargado el 2026-06-18. Roboflow puede regenerar el zip del
# export (otra marca de tiempo interna): si no coincide, manda la verificación por imagen.
EXPECTED_SHA_V27="b2aa413f5e3a3691178df94ba0b8000c2bd671791506f945244908311c478adf"

: "${ROBOFLOW_API_KEY:?Set ROBOFLOW_API_KEY before running this script}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/construction_site_safety"
ZIP_PATH="${RAW_DIR}/${PROJECT}-v${VERSION}-${FORMAT}.zip"
# yolov8 export from Roboflow includes train/valid/test subdirs and data.yaml
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

ACTUAL_SHA="$(sha256sum "${ZIP_PATH}" | cut -d' ' -f1)"
echo "sha256: ${ACTUAL_SHA}"
if [[ "${VERSION}" == "27" ]]; then
  if [[ "${ACTUAL_SHA}" == "${EXPECTED_SHA_V27}" ]]; then
    echo "SHA256 OK (el mismo zip que el 2026-06-18)"
  else
    echo "AVISO: el zip difiere del de 2026-06-18; verificar las imágenes con datasets/registry/imagenes_obra_y_mocs.sha256" >&2
  fi
fi

if command -v unzip >/dev/null 2>&1; then
  unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
  echo "Extracted into: ${RAW_DIR}"
else
  echo "unzip not available; archive at ${ZIP_PATH}"
fi

echo "Image count:"; find "${RAW_DIR}" -type f \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' \) | wc -l

# Print class list from data.yaml so you can verify it matches DatasetConfig.classes
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
    # fallback: grep names from file
    import re, pathlib
    txt = pathlib.Path('${DATA_YAML}').read_text()
    for line in txt.splitlines():
        if re.match(r'\s*[-\d]', line): print(' ', line)
"
fi
