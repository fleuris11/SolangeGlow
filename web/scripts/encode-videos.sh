#!/bin/sh
# Short silent loops for the demonstration pages, from the originals in .media-cache
# (scripts/fetch-media.mjs). Uses the ffmpeg of the backend image:
#   docker compose run --rm --no-deps -v "$PWD/web:/web" -w /web --entrypoint sh backend scripts/encode-videos.sh
# At most 8 seconds, no sound, at most 1.5 MB: the quality drops until the file fits.
set -eu

MAX_BYTES=1572864
SECONDS_MAX=8
OUT=public/media/video
mkdir -p "$OUT"

for source in .media-cache/*.video; do
  slug=$(basename "$source" .video)
  for crf in 28 31 34 37; do
    ffmpeg -y -loglevel error -i "$source" -t "$SECONDS_MAX" -an \
      -vf "scale='min(720,iw)':-2,fps=24" -c:v libx264 -preset slow -crf "$crf" \
      -pix_fmt yuv420p -movflags +faststart "$OUT/$slug.mp4"
    size=$(wc -c <"$OUT/$slug.mp4")
    [ "$size" -le "$MAX_BYTES" ] && break
  done
  ffmpeg -y -loglevel error -i "$OUT/$slug.mp4" -frames:v 1 -vf "scale='min(720,iw)':-2" \
    -c:v libwebp -quality 70 "$OUT/$slug.webp"
  echo "$slug: $size bytes"
done
