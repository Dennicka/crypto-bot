# PropBot Arbitrage Suite

PropBot is a two-venue (Binance + OKX) spot arbitrage bot with SAFE_MODE guard rails, multi-environment configs, API/UX wiring, real REST/WS-ready connectors, and E2E bootstrap scripts. This repository delivers an installable bundle that can run locally in paper mode, migrate to exchange testnets, and prepare for guarded live deployment.

## Components
- **Engine**: Auto-spread evaluator with configurable spread/size thresholds, cooldowns, and execution journaling.
- **API/UI**: FastAPI service exposing dashboards, health/readiness, recon, metrics, and control-state endpoints.
- **Connectors**: REST-signed Binance Spot + OKX Spot integrations with simulated fallbacks for paper mode.
- **Metrics**: Prometheus-compatible counters/gauges for SLO observability.
- **Scripts**: First-run wizard, bootstrap validation, per-profile launchers, and live/demo trade helpers.
- **Configs**: Per-environment YAML definitions for venues, SAFE_MODE, risk, and storage.
- **Tests & CI**: Pytest suite, Ruff, and Mypy guardrails.

## Quick Start
1. Run the wizard to set up the environment:
   ```bash
   ./scripts/00_first_run_wizard.sh
   ```
2. Execute the bootstrap validation pipeline:
   ```bash
   ./scripts/01_bootstrap_and_check.sh
   ```
3. Launch the paper-mode demo service:
   ```bash
   ./scripts/02_demo_paper.sh
   ```
4. Visit `http://localhost:8000/dashboard` for the live dashboard UI.

### Profiles & Connectors
- Paper mode runs entirely offline using simulated connectors; API keys are optional.
- Testnet/live profiles load real REST connectors. Populate `.env` with Binance/OKX keys + passphrase and run:
  ```bash
  ./scripts/start_profile.sh testnet
  ```
- Use `./scripts/demo_trade.sh` to poll `/api/arb/opportunities`, `/api/ui/pnl`, and `/api/ui/exposure` while waiting for spreads above the configured threshold.

## Documentation
Detailed operational guidance lives under `docs/` and feature-specific notes under `FEATURE_GUIDES/`.
