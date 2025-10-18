#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 0 ]]; then
  PROFILE=$1
  shift
else
  PROFILE=${DEFAULT_PROFILE:-paper}
fi
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}
CONFIG="configs/config.${PROFILE}.yaml"

if [[ ! -f "$CONFIG" ]]; then
  echo "[start_profile] Config '$CONFIG' not found" >&2
  exit 1
fi

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

CMD=(python -X dev main.py run --config "$CONFIG" --host "$HOST" --port "$PORT")
if [[ -f .env ]]; then
  CMD+=(--env-file .env)
fi
if [[ $# -gt 0 ]]; then
  CMD+=("$@")
fi

echo "[start_profile] Launching profile '$PROFILE' using $CONFIG"
exec "${CMD[@]}"
