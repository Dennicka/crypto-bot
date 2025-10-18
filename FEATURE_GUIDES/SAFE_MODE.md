# SAFE_MODE Guard Rails

- SAFE_MODE is configurable per environment via `configs/config.*.yaml`.
- When enabled, the engine boots in HOLD and requires two resume confirmations.
- `/api/ui/control-state` exposes status, `/api/ui/control-state/safe-mode` toggles it.
- Execution path short-circuits while SAFE_MODE is active to prevent live fills.
- `/dashboard` displays a SAFE_MODE banner and disables `POST /api/arb/execute` buttons while enabled.
- Runtime overrides via `/api/ui/config/apply` respect SAFE_MODE; spreads/notional thresholds can be updated before resuming live execution.
- `./scripts/start_profile.sh <profile>` always honours SAFE_MODE defaults from the selected config.
