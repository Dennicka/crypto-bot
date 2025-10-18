#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
python main.py run --config configs/config.testnet.yaml
