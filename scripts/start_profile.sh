#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-paper}"           # paper | testnet | live
PORT="${PORT:-8000}"
CFG="configs/config.$PROFILE.yaml"
BASE_URL="http://127.0.0.1:$PORT"

# перейти в корень проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# venv
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# ВАЖНО: защитить PYTHONPATH, если он ещё пустой
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

# на всякий случай, чтобы были базовые зависимости
python -m pip install -U pip wheel >/dev/null 2>&1 || true
python -m pip install fastapi uvicorn pydantic python-dotenv aiofiles jinja2 httpx pyyaml prometheus-client typer rich >/dev/null 2>&1 || true

# если нет конфигурации — создать минимальную
if [ ! -f "$CFG" ]; then
  mkdir -p configs
  cat > "$CFG" <<YAML
mode: "$PROFILE"
safe_mode:
  enabled: false
venues:
  binance:
    name: "binance"
    type: "spot"
    trading_pairs: ["BTC/USDT", "ETH/USDT"]
    taker_fee_bps: 7.5
  okx:
    name: "okx"
    type: "spot"
    trading_pairs: ["BTC/USDT", "ETH/USDT"]
    taker_fee_bps: 7.5
risk:
  max_notional: 50
  max_open_orders: 2
storage:
  path: "data/propbot.sqlite"
YAML
fi

# прибьём старые uvicorn, чтобы не было занятых портов
pkill -f "uvicorn" 2>/dev/null || true

echo "[*] Starting $PROFILE on $BASE_URL with $CFG ..."
python main.py run --config "$CFG" --host 127.0.0.1 --port "$PORT" &

# ждём сервер
sleep 2

# если нет вспомогательных скриптов — прекращать не будем
if [ -x scripts/ui_control.sh ]; then
  ./scripts/ui_control.sh safe-off || true
  ./scripts/ui_control.sh resume   || true
fi

echo "→ GET /live-readiness"
curl -sS "$BASE_URL/live-readiness" || true
echo
echo "→ GET /api/ui/recon/positions"
curl -sS "$BASE_URL/api/ui/recon/positions" || true
echo
echo "→ GET /api/ui/recon/balances"
curl -sS "$BASE_URL/api/ui/recon/balances" || true
echo

echo "→ Watching /api/opportunities (Ctrl+C to stop)"
if [ -x scripts/opps_watch.sh ]; then
  ./scripts/opps_watch.sh
else
  # fallback если нет opps_watch.sh
  while :; do
    ts="$(date '+%H:%M:%S')"
    body="$(curl -sS "$BASE_URL/api/opportunities" || echo '{}')"
    echo "[$ts] $body"
    sleep 2
  done
fi
