#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://127.0.0.1:8000}
INTERVAL=${INTERVAL:-2}
ENGINE_MIN_SPREAD=$(curl -fsS "$BASE_URL/api/ui/status/overview" 2>/dev/null | python - <<'PY' 2>/dev/null || echo 0)
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get("engine", {}).get("min_spread_bps", 0))
except json.JSONDecodeError:
    print(0)
PY
ENGINE_MIN_SPREAD=${ENGINE_MIN_SPREAD:-0}

echo "[demo_trade] Monitoring opportunities >= ${ENGINE_MIN_SPREAD} bps from $BASE_URL"

while true; do
  OPP_JSON=$(curl -fsS "$BASE_URL/api/arb/opportunities" || echo '{}')
  BEST_LINE=$(python - <<'PY' <<<"$OPP_JSON")
import json, sys
data = json.load(sys.stdin)
opps = data.get("opportunities", [])
if not opps:
    print("none 0")
else:
    best = max(opps, key=lambda x: x.get("spread_bps", 0))
    print(f"{best.get('symbol')} {best.get('spread_bps', 0):.2f}")
PY
  read -r SYMBOL SPREAD <<<"$BEST_LINE"
  echo "[demo_trade] Best opportunity: $SYMBOL @ ${SPREAD}bps"
  if [[ "$SYMBOL" != "none" && $(python - <<PY 2>/dev/null || echo False)
print(float('$SPREAD') >= float('$ENGINE_MIN_SPREAD'))
PY
 == "True" ]]; then
    echo "[demo_trade] Waiting for engine execution..."
    sleep "$INTERVAL"
    PNL=$(curl -fsS "$BASE_URL/api/ui/pnl")
    EXPOSURE=$(curl -fsS "$BASE_URL/api/ui/exposure")
    echo "[demo_trade] PnL: $PNL"
    echo "[demo_trade] Exposure: $EXPOSURE"
  else
    echo "[demo_trade] Spread below threshold; sleeping $INTERVAL s"
    sleep "$INTERVAL"
  fi
done
