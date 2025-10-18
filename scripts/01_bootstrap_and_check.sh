#!/usr/bin/env bash
set -euo pipefail

if [[ -d .venv ]]; then
  source .venv/bin/activate
fi

echo "[Bootstrap] Running lint checks..."
ruff check .

echo "[Bootstrap] Running mypy..."
mypy propbot

echo "[Bootstrap] Running pytest..."
pytest

echo "[Bootstrap] Generating readiness snapshot..."
python main.py snapshot --config configs/config.paper.yaml

echo "[Bootstrap] Launching API for smoke checks..."
python main.py run --config configs/config.paper.yaml --host 127.0.0.1 --port 8765 >/tmp/propbot_api.log 2>&1 &
API_PID=$!
sleep 4

function finish {
  if kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap finish EXIT

echo "[Bootstrap] Checking /dashboard endpoint..."
if curl -fsS "http://127.0.0.1:8765/dashboard" >/dev/null; then
  echo "[Bootstrap] /dashboard responded with 200 OK"
else
  echo "[Bootstrap] /dashboard check failed" >&2
  exit 1
fi

echo "[Bootstrap] Checking health endpoint..."
curl -fsS "http://127.0.0.1:8765/api/health" >/dev/null

echo "[Bootstrap] Checking live readiness..."
curl -fsS "http://127.0.0.1:8765/live-readiness" >/dev/null

echo "[Bootstrap] Checking opportunities endpoint..."
curl -fsS "http://127.0.0.1:8765/api/arb/opportunities" >/dev/null

echo "[Bootstrap] Checking status overview..."
curl -fsS "http://127.0.0.1:8765/api/ui/status/overview" >/dev/null

finish
trap - EXIT
