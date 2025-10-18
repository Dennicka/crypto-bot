#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PATCH='{
  "safe_mode": { "enabled": false, "require_double_confirmation": false },
  "engine": {
    "auto_trade": true,
    "min_spread_bps": 7.0,
    "cooldown_s": 2.0,
    "notional": 150.0,
    "max_open_trades": 1
  }
}'
echo "→ validate"
curl -sS -H 'Content-Type: application/json' -d "$PATCH" \
  "$BASE_URL/api/ui/config/validate" | /usr/bin/python3 scripts/pretty_json.py
echo "→ apply"
curl -sS -H 'Content-Type: application/json' -d "$PATCH" \
  "$BASE_URL/api/ui/config/apply" | /usr/bin/python3 scripts/pretty_json.py
echo "→ health"
curl -sS "$BASE_URL/api/health" | /usr/bin/python3 scripts/pretty_json.py
