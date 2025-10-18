#!/usr/bin/env bash
set -u
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
echo "BASE_URL: $BASE_URL"
echo
echo "=== HEALTH ==="
curl -sS --max-time 5 "$BASE_URL/api/health" | /usr/bin/python3 -m json.tool || true
echo
echo "=== READINESS ==="
curl -sS --max-time 5 "$BASE_URL/live-readiness" | /usr/bin/python3 -m json.tool || true
echo
echo "=== OPPORTUNITIES (one-shot) ==="
curl -sS --max-time 5 "$BASE_URL/api/opportunities" | /usr/bin/python3 -m json.tool || true
