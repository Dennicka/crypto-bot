# Dashboard UX

- Single-page dashboard served at `/dashboard` (FastAPI `StaticFiles` mount).
- Four sections: Setup Wizard, Arb Monitor, Status & Limits, and Accounts.
- Poll cadence (5s) hitting `/api/health`, `/live-readiness`, `/api/ui/status/overview`, `/api/arb/opportunities`, and `/api/live/{venue}/account`.
- Execute buttons wire to `POST /api/arb/execute` and are hard-disabled while SAFE_MODE is enabled (dry-run messaging shown).
- Accounts cards display whether API credentials are configured vs simulated balances.
- Built bundle lives under `propbot/ui/dashboard/`; no Node tooling required at runtime.
- Status & Limits column includes live engine thresholds (min spread, notional, cooldown) sourced from `/api/ui/status/overview` and updates immediately after `/api/ui/config/apply` calls.
- Exposure + PnL data in Arb Monitor refresh from `/api/ui/pnl` and `/api/ui/exposure`, mirroring the `demo_trade.sh` helper output.
