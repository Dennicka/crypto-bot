#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
if command -v open >/dev/null 2>&1; then
  open "$BASE_URL/" >/dev/null 2>&1 || true
  open "$BASE_URL/docs" >/dev/null 2>&1 || true
else
  echo "Open manually: $BASE_URL/  and  $BASE_URL/docs"
fi
