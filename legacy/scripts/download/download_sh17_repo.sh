#!/usr/bin/env bash
# DEPRECATED (2026-06-17): SH17 not selected for v2. Use v2 download scripts instead.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/sh17"
ZIP_PATH="${RAW_DIR}/SH17dataset-master.zip"
URL="https://github.com/ahmadmughees/SH17dataset/archive/refs/heads/master.zip"

mkdir -p "${RAW_DIR}"

if [[ -f "${ZIP_PATH}" ]]; then
  echo "File already exists: ${ZIP_PATH}"
else
  curl -L "${URL}" -o "${ZIP_PATH}"
fi

sha256sum "${ZIP_PATH}"
unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
echo "Extracted into: ${RAW_DIR}"
echo "Note: Kaggle dataset files require Kaggle access or manual download. This script preserves the official GitHub source, URL list and helper scripts."
