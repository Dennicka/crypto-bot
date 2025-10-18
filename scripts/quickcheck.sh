#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; C=$'\033[36m'; N=$'\033[0m'

h_raw="$(curl -sS --max-time 5 "$BASE_URL/api/health" || echo '{}')"
r_raw="$(curl -sS --max-time 5 "$BASE_URL/live-readiness" || echo '{}')"

safe="$(printf "%s" "$h_raw" | /usr/bin/python3 - <<'PY'
import sys, json
try:
  d=json.load(sys.stdin)
  print(str(d.get("safe_mode")))
except: print("Unknown")
PY
)"
ready="$(printf "%s" "$r_raw" | /usr/bin/python3 - <<'PY'
import sys, json
try:
  d=json.load(sys.stdin)
  print(str(d.get("ready")))
except: print("Unknown")
PY
)"

echo -n "SAFE_MODE: "; [[ "$safe" == "False" ]] && echo "${G}false${N}" || echo "${Y}${safe}${N}"
echo -n "READY:     "; [[ "$ready" == "True"  ]] && echo "${G}true${N}"  || echo "${R}${ready}${N}"
echo "${C}— OPPS(one-shot) —${N}"
curl -sS --max-time 5 "$BASE_URL/api/opportunities" | /usr/bin/python3 scripts/pretty_json.py
