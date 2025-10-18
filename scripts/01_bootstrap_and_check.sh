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
