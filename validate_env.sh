#!/usr/bin/env bash
set -euo pipefail

REQUIRED=(BINANCE_API_KEY BINANCE_API_SECRET OKX_API_KEY OKX_API_SECRET)
MISSING=()
for key in "${REQUIRED[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    MISSING+=("$key")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "Missing environment variables: ${MISSING[*]}" >&2
  exit 1
fi

echo "Environment validated."
