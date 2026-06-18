#!/usr/bin/env bash
# DEPRECATED (2026-06-17): SH17 not selected for v2. Use v2 download scripts instead.
# Download SH17 images from their original Pexels URLs (no Kaggle credentials needed).
# Images are saved next to the already-versioned labels at datasets/raw/sh17/kaggle/images/.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CSV="${ROOT_DIR}/datasets/raw/sh17/SH17dataset-master/data/list_of_all_urls.csv"
IMG_DIR="${ROOT_DIR}/datasets/raw/sh17/kaggle/images"

mkdir -p "${IMG_DIR}"

# Pexels sits behind Cloudflare, which stalls wget's default User-Agent.
# Use curl with a browser UA; skip files already present (resumable).
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

while IFS= read -r url; do
  [[ -z "${url}" ]] && continue
  fname="$(basename "${url}")"
  out="${IMG_DIR}/${fname}"
  [[ -s "${out}" ]] && continue   # already downloaded
  curl -sSL --fail --max-time 60 -A "${UA}" "${url}" -o "${out}" \
    || { echo "FAILED: ${url}" >&2; rm -f "${out}"; }
done < "${CSV}"

echo "SH17 images present: $(find "${IMG_DIR}" -type f | wc -l) (expected 8099)"
