# E2E Acceptance Evidence

1. **Bootstrap Checks**
   - `./scripts/01_bootstrap_and_check.sh` runs Ruff, Mypy, and Pytest. All must exit 0.
2. **Health Probes**
   - `curl http://localhost:8000/api/health` → `{ "status": "ok", "mode": "paper", ... }`
   - `curl http://localhost:8000/live-readiness` → `{"ready": true, ...}` once resume confirmed.
3. **Arbitrage API**
   - `curl http://localhost:8000/api/opportunities` returns recent opportunities with spread bps.
   - `curl http://localhost:8000/api/ui/exposure` exposes per-venue balances.
4. **Control Plane**
   - `curl -X POST http://localhost:8000/api/ui/control-state/hold -d '{"reason":"dry-run"}'`
   - `curl -X POST http://localhost:8000/api/ui/control-state/resume` twice to exit SAFE_MODE hold.
5. **Metrics & SLO**
   - `curl http://localhost:8000/metrics` includes `spread_bps` histogram, `balance` gauges, and PnL gauge.
   - `curl http://localhost:8000/metrics/latency` returns JSON with ws/order cycle latency targets.
6. **Mode Switch**
   - Paper demo: `./scripts/02_demo_paper.sh`
   - Testnet shadow: `./scripts/03_demo_testnet.sh`
   - Live readiness: `python main.py run --config configs/config.live.yaml`
