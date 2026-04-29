#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${SHUJUJI_DATA_ROOT:-/data/shujuji_annotation}"
TOKEN_FILE="${SHUJUJI_ADMIN_TOKEN_FILE:-$DATA_ROOT/admin_export_token.txt}"
BASE_URL="${SHUJUJI_LOCAL_BASE_URL:-http://127.0.0.1:8787}"
RETENTION_DAYS="${SHUJUJI_EXPORT_RETENTION_DAYS:-30}"

if [ ! -s "$TOKEN_FILE" ]; then
  echo "admin token file not found: $TOKEN_FILE" >&2
  exit 0
fi

ADMIN_TOKEN=$(cat "$TOKEN_FILE")
EXPORT_DIR="$DATA_ROOT/exports"
mkdir -p "$EXPORT_DIR"

curl -fsS -X POST "$BASE_URL/api/admin/export" \
  -H "x-shujuji-admin-token: $ADMIN_TOKEN" \
  -o "$EXPORT_DIR/latest_auto_export_response.json"

find "$EXPORT_DIR" -type f -name 'shujuji_annotation_export_*.json' -mtime +"$RETENTION_DAYS" -delete
find "$EXPORT_DIR" -type f -name 'shujuji_annotation_export_*.manifest.json' -mtime +"$RETENTION_DAYS" -delete

cat "$EXPORT_DIR/latest_auto_export_response.json"
