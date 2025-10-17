# PropBot Arbitrage Suite

PropBot is a two-venue (Binance + OKX) spot arbitrage bot with SAFE_MODE guard rails, multi-environment configs, API/UX wiring, and E2E bootstrap scripts. This repository delivers an installable bundle that can run locally in paper mode, migrate to testnet, and prepare for guarded live deployment.

## Components
- **Engine**: Simulated two-venue arbitrage loop with execution safety gates and journaling.
- **API/UI**: FastAPI service exposing dashboards, health/readiness, recon, metrics, and control-state endpoints.
- **Metrics**: Prometheus-compatible counters/gauges for SLO observability.
- **Scripts**: First-run wizard, bootstrap validation, and demo launchers for paper/testnet modes.
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

## Documentation
Detailed operational guidance lives under `docs/` and feature-specific notes under `FEATURE_GUIDES/`.
