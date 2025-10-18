#!/usr/bin/env bash
set -euo pipefail

PROFILE=${DEFAULT_PROFILE:-paper}
REQUIRED=(BINANCE_API_KEY BINANCE_API_SECRET OKX_API_KEY OKX_API_SECRET OKX_PASSPHRASE)
MISSING=()

if [[ "$PROFILE" != "paper" ]]; then
  for key in "${REQUIRED[@]}"; do
    if [[ -z "${!key:-}" ]]; then
      MISSING+=("$key")
    fi
  done
else
  echo "Running in paper mode: credential checks skipped."
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "Missing environment variables for profile '$PROFILE': ${MISSING[*]}" >&2
  exit 1
fi

echo "Environment validated for profile '$PROFILE'."
