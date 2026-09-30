#!/usr/bin/env bash
# 画面録画。使い方: ./scripts/rec.sh [モニター名|frame] [補足]  止めるときは q
#   frame : HDMI-0 左上の 1920x1080 固定範囲（提出動画用）。位置は FRAME_OFF=x,y で変更可
set -euo pipefail
mountpoint -q /mnt/llm-storage || { echo "SSD 未マウント" >&2; exit 1; }
MON="${1:-HDMI-0}"; TAG="${2:-}"; GEOM=""; OFF=""
if [[ "$MON" == "frame" ]]; then
  GEOM="1920x1080"; OFF="${FRAME_OFF:-0,0}"
else
  read -r GEOM OFF < <(xrandr --listmonitors | awk -v m="$MON" '$NF==m{split($3,a,/[\/x+]/); print a[1]"x"a[3], a[5]","a[6]}') || true
fi
[[ -n "$GEOM" ]] || { echo "モニター $MON なし" >&2; xrandr --listmonitors >&2; exit 1; }
OUT="/mnt/llm-storage/pai-final/recordings/$(date +%Y%m%d_%H%M%S)${TAG:+_$TAG}.mp4"
echo "録画: $MON ($GEOM, 位置 $OFF) → $OUT   止めるときは q"
exec ffmpeg -hide_banner -loglevel warning -stats -f x11grab -framerate 30 -video_size "$GEOM" -i "${DISPLAY}+${OFF}" -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -movflags +frag_keyframe+empty_moov+default_base_moof "$OUT"
