#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

pp() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  elif command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import sys, json
data = sys.stdin.read()
try:
    print(json.dumps(json.loads(data), ensure_ascii=False, indent=2))
except Exception:
    print(data)
PY
  else
    cat
  fi
}

req() {
  local method="$1"; shift
  local path="$1"; shift
  local data="${1-}"

  if [ -n "$data" ]; then
    resp="$(curl -sS -H 'Content-Type: application/json' -X "$method" \
                 --data-raw "$data" "$BASE_URL$path" -w $'\n__HTTP__:%{http_code}')"
  else
    resp="$(curl -sS -X "$method" "$BASE_URL$path" -w $'\n__HTTP__:%{http_code}')"
  fi

  body="${resp%__HTTP__:*}"; code="${resp##*__HTTP__:}"
  echo "HTTP $code"
  printf "%s" "$body" | pp
  return 0
}

case "${1:-}" in
  status)     echo "→ GET /api/ui/control-state"; req GET "/api/ui/control-state" ;;
  hold)       reason="${2:-manual}"; echo "→ POST /api/ui/control-state/hold"; req POST "/api/ui/control-state/hold" "{\"reason\":\"$reason\"}" ;;
  resume)     echo "→ POST /api/ui/control-state/resume"; req POST "/api/ui/control-state/resume" ;;
  safe-on)    echo "→ POST /api/ui/control-state/safe-mode {enabled:true}"; req POST "/api/ui/control-state/safe-mode" '{"enabled": true}' ;;
  safe-off)   echo "→ POST /api/ui/control-state/safe-mode {enabled:false}"; req POST "/api/ui/control-state/safe-mode" '{"enabled": false}' ;;
  health)     echo "→ GET /api/health"; req GET "/api/health" ;;
  readiness)  echo "→ GET /live-readiness"; req GET "/live-readiness" ;;
  opps)       echo "→ GET /api/opportunities"; req GET "/api/opportunities" ;;
  *)
    cat <<USAGE
Usage:
  $0 status | hold "manual" | resume | safe-on | safe-off | health | readiness | opps
USAGE
  ;;
esac
