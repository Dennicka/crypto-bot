#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.."; pwd)"
cd "$ROOT"

PORT="${PORT:-8000}"
BASE_URL="http://127.0.0.1:$PORT"

# окружение
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export NO_PROXY="127.0.0.1,localhost"
[[ -f .venv/bin/activate ]] && source .venv/bin/activate
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

# чистый старт
pkill -f "uvicorn|main.py run" 2>/dev/null || true
sleep 0.5

# сервер в фоне + лог
mkdir -p logs .run
ts="$(date +%Y%m%d-%H%M%S)"
nohup python -X dev main.py run --config configs/config.paper.yaml \
      --host 127.0.0.1 --port "$PORT" \
      > "logs/server.$ts.log" 2>&1 & echo $! > .run/server.pid
disown
echo "→ server starting (pid $(cat .run/server.pid)), log: logs/server.$ts.log"

# ждём /api/health до 60 сек, без падения при ошибках
for i in $(seq 1 60); do
  if curl -s --max-time 1 "$BASE_URL/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  [[ "$i" == "60" ]] && { echo "❌ API not responding. Check: tail -n 80 logs/server.$ts.log"; exit 1; }
done

# снимаем safe_mode
curl -s --max-time 5 -H 'Content-Type: application/json' \
  -d '{"enabled": false}' \
  "$BASE_URL/api/ui/control-state/safe-mode" >/dev/null || true

# включаем автоторговлю
PATCH='{
  "engine": { "auto_trade": true, "min_spread_bps": 7.0, "cooldown_s": 2.0, "notional": 150.0, "max_open_trades": 1 }
}'
curl -s --max-time 5 -H 'Content-Type: application/json' \
  -d "$PATCH" \
  "$BASE_URL/api/ui/config/apply" >/dev/null || true

# ждём ready:true до 30 сек
for i in $(seq 1 30); do
  ready="$(curl -s --max-time 2 "$BASE_URL/live-readiness" | /usr/bin/python3 - <<'PY'
import sys,json
try: print(str(json.load(sys.stdin).get("ready")))
except: print("False")
PY
)"
  [[ "$ready" == "True" ]] && break || sleep 1
  [[ "$i" == "30" ]] && echo "⚠️ ready:false — это не критично, движок может ещё прогреваться."
done

# короткий статус
./scripts/status.sh || true

# открываем дашборд и swagger
if command -v open >/dev/null 2>&1; then
  open "$BASE_URL/" >/dev/null 2>&1 || true
  open "$BASE_URL/docs" >/dev/null 2>&1 || true
fi

echo "✅ Bot is up. Watch signals:  ./scripts/opps_watch.sh"
echo "   Stop bot:                 ./scripts/stop_bot.sh"
echo "   Logs: tail -f logs/server.$ts.log"
