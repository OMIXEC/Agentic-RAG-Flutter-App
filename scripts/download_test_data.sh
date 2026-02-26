#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT_DIR/data/image" "$ROOT_DIR/data/video" "$ROOT_DIR/data/audio" "$ROOT_DIR/data/txt"

curl -L "https://picsum.photos/seed/ragtest1/640/360" -o "$ROOT_DIR/data/image/news-random-1.jpg"
curl -L "https://samplelib.com/lib/preview/mp4/sample-5s.mp4" -o "$ROOT_DIR/data/video/sample-5s.mp4"
curl -L "https://samplelib.com/lib/preview/mp3/sample-3s.mp3" -o "$ROOT_DIR/data/audio/sample-3s.mp3"

cat > "$ROOT_DIR/data/txt/random_news_download_note.txt" <<'NOTE'
Downloaded random media assets for multimodal tests.
Sources:
- https://picsum.photos/
- https://samplelib.com/
NOTE

echo "Download complete."
