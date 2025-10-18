# Arbitrage Engine Overview

1. `Scheduler` polls Binance and OKX connectors every tick, falling back to simulated data in paper mode.
2. `ArbitrageEngine.evaluate` computes spreads per shared symbol and admits opportunities only when `spread_bps > max(engine.min_spread_bps, taker_fees + engine.safety_margin_bps)`.
3. `_execute_if_allowed` enforces SAFE_MODE and cooldown gates; real connectors submit signed orders while simulated connectors update balances locally.
4. Journaling stores both opportunities and executions, including realized PnL and connector responses.
5. `run_rebalancer` refreshes venue balances, establishes the portfolio baseline, and updates realized/unrealized PnL gauges for the UI and Prometheus endpoints.
