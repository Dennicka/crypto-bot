# Arbitrage Engine Overview

1. `Scheduler` polls Binance and OKX connectors for synthetic order books every second.
2. `ArbitrageEngine.evaluate` computes spreads and records opportunities when threshold > 5 bps.
3. Executions run only when SAFE_MODE disabled; fill simulation updates balances and journal.
4. Metrics update `spread_bps`, `order_cycle_ms_p95`, and PnL gauges.
5. `run_rebalancer` syncs gauge values for UI/metrics dashboards.
