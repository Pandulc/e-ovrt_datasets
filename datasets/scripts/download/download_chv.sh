#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/chv"
FILE_ID="1fdGn67W0B7ShpBDbbQpUF0ScPQa4DR0a"
ZIP_PATH="${RAW_DIR}/CHV_dataset.zip"
CONFIRM_HTML="${RAW_DIR}/.chv_drive_confirm.html"

mkdir -p "${RAW_DIR}"

if [[ ! -f "${ZIP_PATH}" ]]; then
  curl -L "https://drive.google.com/uc?export=download&id=${FILE_ID}" -o "${CONFIRM_HTML}"
  CONFIRM="$(sed -n 's/.*name="confirm" value="\([^"]*\)".*/\1/p' "${CONFIRM_HTML}" | head -1)"
  UUID="$(sed -n 's/.*name="uuid" value="\([^"]*\)".*/\1/p' "${CONFIRM_HTML}" | head -1)"
  if [[ -z "${CONFIRM}" || -z "${UUID}" ]]; then
    echo "Could not extract Google Drive confirmation token." >&2
    exit 1
  fi
  curl -L "https://drive.usercontent.google.com/download?id=${FILE_ID}&export=download&confirm=${CONFIRM}&uuid=${UUID}" -o "${ZIP_PATH}"
fi

sha256sum "${ZIP_PATH}"

if command -v unzip >/dev/null 2>&1; then
  unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
  echo "Extracted into: ${RAW_DIR}"
else
  echo "unzip not available; archive at ${ZIP_PATH}"
fi
