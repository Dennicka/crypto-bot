# Installation Drop-in

1. **Clone or unzip** the bundle into any directory.
2. **Run the first-run wizard**:
   ```bash
   ./scripts/00_first_run_wizard.sh
   ```
   This provisions a virtualenv, installs dependencies, validates `.env`, and copies the paper config.
3. **Validate** via the bootstrap script:
   ```bash
   ./scripts/01_bootstrap_and_check.sh
   ```
4. **Launch** the desired environment:
   - Paper: `./scripts/02_demo_paper.sh`
   - Testnet: `./scripts/03_demo_testnet.sh`
5. **Access** the dashboard at `http://localhost:8000` and confirm `/api/health` responds `ok`.
