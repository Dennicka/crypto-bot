#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
INTERVAL="${INTERVAL:-2}"
while :; do
  curl -sS --max-time 5 "$BASE_URL/api/ui/execution" | /usr/bin/python3 scripts/pretty_json.py
  sleep "$INTERVAL"
done
