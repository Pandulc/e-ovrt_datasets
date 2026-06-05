#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <dataset_id>" >&2
  exit 2
fi

DATASET_ID="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RAW_DIR="${ROOT_DIR}/datasets/raw/${DATASET_ID}"

if [[ ! -d "${RAW_DIR}" ]]; then
  echo "Raw dataset directory does not exist: ${RAW_DIR}" >&2
  exit 1
fi

echo "dataset_id: ${DATASET_ID}"
echo "raw_dir: ${RAW_DIR}"
echo "total_files: $(find "${RAW_DIR}" -type f | wc -l)"
echo "total_size_bytes: $(du -sb "${RAW_DIR}" | awk '{print $1}')"
echo "image_files: $(find "${RAW_DIR}" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.bmp' -o -iname '*.webp' \) | wc -l)"
echo "xml_annotations: $(find "${RAW_DIR}" -type f -iname '*.xml' | wc -l)"
echo "txt_annotations: $(find "${RAW_DIR}" -type f -iname '*.txt' | wc -l)"
echo "json_annotations: $(find "${RAW_DIR}" -type f -iname '*.json' | wc -l)"

echo "sample_files:"
(find "${RAW_DIR}" -type f | sort | head -20) || true
