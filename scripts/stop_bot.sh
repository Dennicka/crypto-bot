#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "$0")/.."; pwd)"
pkill -f "uvicorn|main.py run" 2>/dev/null || true
if [[ -f .run/server.pid ]]; then
  pid="$(cat .run/server.pid || true)"
  [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null || true
  rm -f .run/server.pid
fi
echo "🛑 server stopped"
