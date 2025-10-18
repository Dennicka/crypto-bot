# Installation Drop-in

1. **Unpack the bundle**
   ```bash
   unzip propbot_arb_E2E_codex_bundle_vX.zip -d /opt/propbot
   cd /opt/propbot
   ```
   No git checkout or Node.js toolchain is required; the UI bundle ships pre-built under `propbot/ui/dashboard/`.
2. **Run the first-run wizard** (creates `.venv`, installs deps, prepares configs):
   ```bash
   ./scripts/00_first_run_wizard.sh
   ```
3. **Set credentials (optional for paper mode)**
   - Edit `.env` to provide `DEFAULT_PROFILE`, `BINANCE_*`, and `OKX_*` values if you intend to run against testnet/live.
   - Paper simulations work without keys; `validate_env.sh` will skip checks when `DEFAULT_PROFILE=paper`.
4. **Execute acceptance checks**:
   ```bash
   ./scripts/01_bootstrap_and_check.sh
   ```
   The script runs Ruff, Mypy, Pytest, and verifies `/dashboard` + `/api/health` return `200` using a temporary service instance.
5. **Launch the service** with SAFE_MODE defaults:
   - Paper: `./scripts/02_demo_paper.sh`
   - Testnet shadow: `./scripts/03_demo_testnet.sh`
   - Arbitrary profile: `./scripts/start_profile.sh <paper|testnet|live>`
6. **Open the dashboard** at `http://localhost:8000/dashboard`.
   - The UI polls `/api/health`, `/live-readiness`, `/api/arb/opportunities`, `/api/live/{venue}/account`, and `/api/ui/status/overview`.
   - Use `./scripts/demo_trade.sh` to stream spreads, realized PnL, and exposure metrics while the engine reacts to opportunities.
