# SAFE_MODE Guard Rails

- SAFE_MODE is configurable per environment via `configs/config.*.yaml`.
- When enabled, the engine boots in HOLD and requires two resume confirmations.
- `/api/ui/control-state` exposes status, `/api/ui/control-state/safe-mode` toggles it.
- Execution path short-circuits while SAFE_MODE is active to prevent live fills.
- `/dashboard` displays a SAFE_MODE banner and disables `POST /api/arb/execute` buttons while enabled.
