#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-daily}"
case "$MODE" in
  hourly|daily|weekly|manual) ;;
  *)
    echo "Usage: $0 {hourly|daily|weekly|manual}" >&2
    exit 2
    ;;
esac

SRC="${SHUJUJI_DATA_ROOT:-/data/shujuji_annotation}"
BASE="${SHUJUJI_BACKUP_ROOT:-/data/shujuji_annotation_backups}"
DEST="$BASE/$MODE"
mkdir -p "$DEST"

if [ ! -d "$SRC" ]; then
  echo "source not found: $SRC" >&2
  exit 0
fi

STAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="$DEST/shujuji_annotations_${MODE}_${STAMP}.tar.gz"
MANIFEST="$DEST/shujuji_annotations_${MODE}_${STAMP}.manifest.txt"
TMP_ARCHIVE="$ARCHIVE.tmp"
TMP_MANIFEST="$MANIFEST.tmp"
SRC_PARENT=$(dirname "$SRC")
SRC_NAME=$(basename "$SRC")

{
  echo "mode=$MODE"
  echo "created_at=$(date -Is)"
  echo "source=$SRC"
  echo "host=$(hostname)"
  echo "claims_count=$(find "$SRC" -path '*/claims.json' -type f | wc -l)"
  echo "draft_json_count=$(find "$SRC" -path '*/drafts/*' -type f -name '*.json' | wc -l)"
  echo "final_json_count=$(find "$SRC" -path '*/by_annotator/*' -type f -name '*.json' | wc -l)"
  echo "submission_json_count=$(find "$SRC" -path '*/submissions/*' -type f -name '*.json' | wc -l)"
} > "$TMP_MANIFEST"

tar -czf "$TMP_ARCHIVE" -C "$SRC_PARENT" "$SRC_NAME"
mv "$TMP_ARCHIVE" "$ARCHIVE"
sha256sum "$ARCHIVE" >> "$TMP_MANIFEST"
mv "$TMP_MANIFEST" "$MANIFEST"

ln -sfn "$ARCHIVE" "$BASE/latest_${MODE}.tar.gz"
ln -sfn "$MANIFEST" "$BASE/latest_${MODE}.manifest.txt"

find "$BASE/hourly" -type f \( -name '*.tar.gz' -o -name '*.manifest.txt' \) -mtime +3 -delete 2>/dev/null || true
find "$BASE/daily" -type f \( -name '*.tar.gz' -o -name '*.manifest.txt' \) -mtime +30 -delete 2>/dev/null || true
find "$BASE/weekly" -type f \( -name '*.tar.gz' -o -name '*.manifest.txt' \) -mtime +90 -delete 2>/dev/null || true
find "$BASE/manual" -type f \( -name '*.tar.gz' -o -name '*.manifest.txt' \) -mtime +180 -delete 2>/dev/null || true

echo "$ARCHIVE"
