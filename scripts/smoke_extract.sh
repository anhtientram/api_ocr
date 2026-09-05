#!/usr/bin/env bash
# Smoke call against local server.
# Usage: ./scripts/smoke_extract.sh [path-to-file]
set -euo pipefail
FILE="${1:-}"
BASE="${BASE_URL:-http://127.0.0.1:8080}"
KEY="${AI_PROXY_SECRET:-dev-secret-change-me}"

curl -sS "$BASE/health" | python3 -m json.tool

if [[ -z "$FILE" ]]; then
  echo "Pass an image/PDF path to test /v1/ocr/extract"
  exit 0
fi

curl -sS -X POST "$BASE/v1/ocr/extract" \
  -H "X-AI-Proxy-Key: $KEY" \
  -F "file=@${FILE}" \
  -F "document_type=lab" \
  -F "include_bbox=true" \
  -F "include_summary=false" | python3 -m json.tool
