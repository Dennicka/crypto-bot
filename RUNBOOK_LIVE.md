# Live / Testnet Runbook

## 1. Acquire Exchange Credentials
- **Binance Spot Testnet**: Register at <https://testnet.binance.vision/> and create API keys with trading permissions.
- **OKX Demo Trading**: Sign in at <https://www.okx.com/demo-trading>, generate API key + secret + passphrase, and enable spot trading.
- For live trading, follow corporate approval before creating production keys and restrict by IP allowlist.

## 2. Configure `.env`
```bash
cp .env.example .env  # if not already present
```
Populate the following variables:
```
DEFAULT_PROFILE=testnet  # or live
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
OKX_API_KEY=...
OKX_API_SECRET=...
OKX_PASSPHRASE=...
```
Validate the environment:
```bash
source .env
./validate_env.sh
```

## 3. Launch the Profile
```bash
./scripts/start_profile.sh testnet
```
The script activates `.venv`, exports `PYTHONPATH`, and launches FastAPI with the correct config/SAFE_MODE gates. For live trading substitute `testnet` with `live`.

## 4. Post-Start Checks
1. Visit `http://127.0.0.1:8000/dashboard` and confirm all four dashboard sections render.
2. Verify `/live-readiness` reports `ready=true` once both order books stream data and SAFE_MODE holds are cleared.
3. Review balances under `/api/live/binance/account` and `/api/live/okx/account`. Missing credentials or network faults are surfaced in the response `message` field.
4. Use `/api/ui/config/validate` to confirm the active profile matches expectations. Adjust runtime spread/notional thresholds via `/api/ui/config/apply` if market conditions change.
5. Tail `/metrics` for execution counters and `/metrics/latency` for health of exchange calls.
6. Run `./scripts/demo_trade.sh` to watch spreads, PnL, and exposure while spreads exceed the configured threshold.

## 5. Operational Notes
- SAFE_MODE defaults to `enabled` with HOLD on startup; clear via two POSTs to `/api/ui/control-state/resume` after review.
- The engine journal persists executions under `data/<profile>_journal.sqlite3`; archive this file per compliance policies.
- Runtime overrides (min spread, notional) survive until process restart; update YAML configs to make changes permanent.

## 6. Rolling Back to Paper
1. Stop the running service (`Ctrl+C` or SIGTERM).
2. Set `DEFAULT_PROFILE=paper` in `.env`.
3. Re-run `./scripts/start_profile.sh paper` to return to simulated mode.
4. Confirm `/api/live/*/account` now returns simulated balances and no exchange orders are placed.
