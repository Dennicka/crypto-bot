# Live Trading Safety Checklist

## Key Risks
- **Exchange Throttling**: Binance and OKX enforce strict REST rate limits. Excessive bursts return HTTP 429 or 418 bans.
- **Credential Leakage**: API keys grant trade privileges; compromise can trigger unwanted fills.
- **Clock Skew**: Signed Binance requests require server time alignment; stale clocks cause signature errors.
- **Abnormal Order Responses**: Exchanges may reject or partially fill orders due to min notional/quantity or circuit breakers.

## Limits & Guards
- SAFE_MODE defaults to HOLD; two confirmations are required before any execution.
- Configurable risk caps in `configs/config.*.yaml`:
  - `risk.max_single_order_usd` restricts per-trade exposure.
  - `engine.min_spread_bps` + `engine.safety_margin_bps` ensure spreads exceed taker fees.
  - `engine.cooldown_ms` throttles executions to avoid rapid-fire orders.
- `/api/ui/config/apply` allows on-call engineers to widen or tighten thresholds without restarts.

## Credential Hygiene
- Store keys in `.env` with restrictive permissions (600) and avoid committing to version control.
- Enable IP allowlists and 2FA on both Binance and OKX portals.
- Rotate keys quarterly and immediately after personnel changes.

## Rate Limit / Error Handling
- On HTTP 429/418 responses, the connectors back off automatically; continue monitoring `/metrics` for `order_book_error_total` and `balance_error_total` spikes.
- For repeated throttling, increase `engine.cooldown_ms` and/or reduce `scheduler.tick_interval_ms`.
- When `abnormal order` errors occur, inspect venue min-notional/min-qty constraints and adjust config accordingly.

## Incident Playbook
1. Toggle HOLD via `/api/ui/control-state/hold` to stop new executions.
2. Inspect `/metrics`, `/api/ui/status/overview`, and journal entries to assess impact.
3. Communicate status to stakeholders and follow `docs/OPERATIONS.md` escalation tree.
4. Resume trading only after verifying balances, exposure, and config thresholds.
