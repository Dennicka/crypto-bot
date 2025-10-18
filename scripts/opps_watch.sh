#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
INTERVAL="${INTERVAL:-2}"
while :; do
  ts="$(date '+%H:%M:%S')"
  body="$(curl -sS --max-time 5 "$BASE_URL/api/opportunities" || echo '{"opportunities": []}')"
  echo "[$ts] $body"
  sleep "$INTERVAL"
done
