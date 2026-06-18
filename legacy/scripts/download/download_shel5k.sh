#!/usr/bin/env bash
# DEPRECATED (2026-06-17): SHEL5K not selected for v2. Use v2 download scripts instead.
# Download SHEL5K from Mendeley Data (public-api zip endpoint) into datasets/raw/shel5k/.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/shel5k"
ZIP_PATH="${RAW_DIR}/9rcv8mm682-4.zip"
URL="https://data.mendeley.com/public-api/zip/9rcv8mm682/download/4"
EXPECTED_SHA="dfba1d3ce01af69d791020cdfdfdbc25904b41724d11160361e7a4cd164e7a7a"

mkdir -p "${RAW_DIR}"

if [[ -f "${ZIP_PATH}" ]]; then
  echo "File already exists: ${ZIP_PATH}"
else
  curl -L --fail --max-time 600 "${URL}" -o "${ZIP_PATH}"
fi

ACTUAL_SHA="$(sha256sum "${ZIP_PATH}" | cut -d' ' -f1)"
echo "sha256: ${ACTUAL_SHA}"
if [[ "${ACTUAL_SHA}" == "${EXPECTED_SHA}" ]]; then
  echo "SHA256 OK (matches documented value)"
else
  echo "WARNING: SHA256 mismatch (expected ${EXPECTED_SHA})" >&2
fi

unzip -q -n "${ZIP_PATH}" -d "${RAW_DIR}"
echo "Extracted into: ${RAW_DIR}"
