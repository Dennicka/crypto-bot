#!/usr/bin/env bash
set -Eeuo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
T="${T:-5}"
pp(){ /usr/bin/python3 scripts/pretty_json.py; }
get(){ curl -sS --max-time "$T" -H 'Accept: application/json' "$BASE_URL$1" | pp; }
post(){ curl -sS --max-time "$T" -X POST -H 'Content-Type: application/json' -d "${2:-{}}" "$BASE_URL$1" | pp; }
case "${1:-}" in
  status)    get /api/ui/control-state ;;
  hold)      post /api/ui/control-state/hold "{\"reason\":\"${2:-manual}\"}" ;;
  resume)    post /api/ui/control-state/resume ;;
  safe-on)   post /api/ui/control-state/safe-mode '{"enabled": true}' ;;
  safe-off)  post /api/ui/control-state/safe-mode '{"enabled": false}' ;;
  health)    get /api/health ;;
  readiness) get /live-readiness ;;
  *) echo "usage: $0 {status|hold|resume|safe-on|safe-off|health|readiness}"; exit 1;;
esac
