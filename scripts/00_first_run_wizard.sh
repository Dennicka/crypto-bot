#!/usr/bin/env bash
set -euo pipefail

echo "[Wizard] Preparing PropBot environment..."
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[Wizard] Created .env from example. Please update API keys before live trading."
fi

echo "[Wizard] Validating environment variables..."
source .env || true
./validate_env.sh || echo "[Wizard] Missing values are acceptable for paper mode."

echo "[Wizard] Installing dependencies (editable mode)..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]

echo "[Wizard] Bootstrapping paper config..."
mkdir -p data/archive
cp configs/config.paper.yaml configs/active.yaml

echo "[Wizard] First run wizard completed. Use './scripts/01_bootstrap_and_check.sh' next."
