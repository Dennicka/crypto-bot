#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "→ /api/health"
curl -sS "$BASE_URL/api/health" && echo -e "\n"

echo "→ /live-readiness"
curl -sS "$BASE_URL/live-readiness" && echo -e "\n"

echo "→ /metrics (первые строки)"
curl -sS "$BASE_URL/metrics" | head -n 25 || true
