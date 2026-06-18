#!/usr/bin/env bash
# DEPRECATED (2026-06-17): construction_ppe not selected for v2. Use v2 download scripts instead.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/construction_ppe"
ZIP_PATH="${RAW_DIR}/construction-ppe.zip"
URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip"

mkdir -p "${RAW_DIR}"

if [[ -f "${ZIP_PATH}" ]]; then
  echo "File already exists: ${ZIP_PATH}"
else
  curl -L "${URL}" -o "${ZIP_PATH}"
fi

sha256sum "${ZIP_PATH}"

if command -v unzip >/dev/null 2>&1; then
  unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
  echo "Extracted into: ${RAW_DIR}"
else
  echo "unzip is not available; downloaded archive only."
fi
