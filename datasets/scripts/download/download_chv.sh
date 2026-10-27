#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/chv"
FILE_ID="1fdGn67W0B7ShpBDbbQpUF0ScPQa4DR0a"
ZIP_PATH="${RAW_DIR}/CHV_dataset.zip"
CONFIRM_HTML="${RAW_DIR}/.chv_drive_confirm.html"
# sha256 del zip descargado el 2026-06-05 (download_log.md), el de las 1.330 imágenes de bench_v3.
EXPECTED_SHA="e2a2ebef7b9a69fd2d7f5152eb808b14a3a0a76de015c802f3f187c437a8e577"

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

ACTUAL_SHA="$(sha256sum "${ZIP_PATH}" | cut -d' ' -f1)"
echo "sha256: ${ACTUAL_SHA}"
if [[ "${ACTUAL_SHA}" == "${EXPECTED_SHA}" ]]; then
  echo "SHA256 OK (el mismo zip que el 2026-06-05)"
else
  echo "AVISO: el zip difiere del de 2026-06-05; verificar las imágenes con datasets/registry/bench_v3_imagenes.sha256" >&2
fi

if command -v unzip >/dev/null 2>&1; then
  unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
  echo "Extracted into: ${RAW_DIR}"
else
  echo "unzip not available; archive at ${ZIP_PATH}"
fi
