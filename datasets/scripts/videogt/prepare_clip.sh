#!/usr/bin/env bash
# datasets/scripts/videogt/prepare_clip.sh
# Etapa 0 del video-gt-lab: normaliza un video fuente a CFR sin audio y emite
# <clip_id>.info.json (los videos de celular suelen ser VFR, que rompe el
# mapeo frame<->ms del pipeline). TODO lo que entra a CVAT pasa por acá.
#
# Uso: prepare_clip.sh <input> <clip_id> [--ss T] [--to T] [--fps N] [--scale WxH]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_DIR="$REPO_ROOT/datasets-videos/clips"

INPUT="${1:?uso: prepare_clip.sh <input> <clip_id> [--ss T] [--to T] [--fps N] [--scale WxH]}"
CLIP_ID="${2:?falta clip_id}"
shift 2

if [[ ! "$CLIP_ID" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "clip_id inválido: '$CLIP_ID' (solo se permite [A-Za-z0-9_-])" >&2
  exit 2
fi
SS="" TO="" FPS=30 SCALE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ss) SS="$2"; shift 2 ;;
    --to) TO="$2"; shift 2 ;;
    --fps) FPS="$2"; shift 2 ;;
    --scale) SCALE="$2"; shift 2 ;;
    *) echo "opción desconocida: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$FPS" =~ ^[0-9]+$ ]]; then
  echo "fps inválido: '$FPS' (debe ser un entero positivo; el pipeline requiere CFR con fps entero para que el mapeo frame↔ms sea exacto)" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/$CLIP_ID.mp4"

FILTERS="fps=$FPS"
[[ -n "$SCALE" ]] && FILTERS="$FILTERS,scale=${SCALE/x/:}"

ARGS=(-y -hide_banner -loglevel error)
[[ -n "$SS" ]] && ARGS+=(-ss "$SS")
ARGS+=(-i "$INPUT")
[[ -n "$TO" ]] && ARGS+=(-to "$TO")
ARGS+=(-an -vf "$FILTERS" -fps_mode cfr -c:v libx264 -crf 18 -preset medium "$OUT")
ffmpeg "${ARGS[@]}"

read -r WIDTH HEIGHT NFRAMES < <(ffprobe -v error -select_streams v:0 -count_frames \
  -show_entries stream=width,height,nb_read_frames -of csv=p=0 "$OUT" | tr ',' ' ')

if [[ -z "${WIDTH:-}" || -z "${HEIGHT:-}" || -z "${NFRAMES:-}" \
      || ! "$WIDTH" =~ ^[0-9]+$ || ! "$HEIGHT" =~ ^[0-9]+$ || ! "$NFRAMES" =~ ^[0-9]+$ ]]; then
  echo "ffprobe no devolvió los campos esperados (width/height/nb_read_frames) para $OUT" >&2
  exit 1
fi

SHA256=$(sha256sum "$OUT" | cut -d' ' -f1)
DURATION_MS=$(python3 -c "print(round($NFRAMES * 1000 / $FPS))")

python3 - "$OUT_DIR/$CLIP_ID.info.json" "$CLIP_ID" "$FPS" "$DURATION_MS" "$NFRAMES" "${WIDTH}x${HEIGHT}" "$SHA256" <<'EOF'
import json, sys

out_path, clip_id, fps, duration_ms, n_frames, resolution, sha256 = sys.argv[1:8]
json.dump({
    "clip_id": clip_id,
    "file": f"clips/{clip_id}.mp4",
    "fps": int(fps),
    "duration_ms": int(duration_ms),
    "n_frames": int(n_frames),
    "resolution": resolution,
    "sha256": sha256,
}, open(out_path, "w"), indent=2)
print(f"✓ {out_path}")
EOF
echo "✓ $OUT  (${WIDTH}x${HEIGHT}, $FPS fps CFR, $NFRAMES frames, ${DURATION_MS} ms)"
