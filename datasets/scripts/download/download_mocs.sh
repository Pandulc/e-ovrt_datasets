#!/usr/bin/env bash
# Downloads the Roboflow copy of MOCS ("mocs-bowib", v1, COCO export) into datasets/raw/MOCS/.
# Requires: ROBOFLOW_API_KEY env var, curl, python3 (for JSON parsing), unzip.
# Usage: ROBOFLOW_API_KEY=<key> bash download_mocs.sh [version]
#
# Es la copia que está en disco desde el 2025-05-22 (datasets_metadata.yaml, id `mocs`): 1.471
# imágenes, solo anota `Worker`, NO el MOCS original de anlab340. Se usa en el piloto de clase
# nueva (EXT-01, split `valid`, 151 imágenes). Uso evaluativo: las imágenes no se redistribuyen
# (license_registry.md). Verificar después, imagen por imagen:
#   sha256sum -c datasets/registry/imagenes_obra_y_mocs.sha256   (desde la raíz del repo)
set -euo pipefail

WORKSPACE="mocs"
PROJECT="mocs-bowib"
VERSION="${1:-1}"
FORMAT="coco"

: "${ROBOFLOW_API_KEY:?Set ROBOFLOW_API_KEY before running this script}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/MOCS"
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

echo "sha256: $(sha256sum "${ZIP_PATH}" | cut -d' ' -f1)"

if command -v unzip >/dev/null 2>&1; then
  unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
  echo "Extracted into: ${RAW_DIR}"
else
  echo "unzip not available; archive at ${ZIP_PATH}"
fi

echo "Images in valid/ (expected 151):"
find "${RAW_DIR}/valid" -maxdepth 1 -type f -name '*.jpg' | wc -l
