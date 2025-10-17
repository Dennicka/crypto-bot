# E2E Acceptance Evidence

## Environment
- Python 3.12.x
- FastAPI 0.109 / Uvicorn 0.24
- Host OS: Ubuntu 22.04 (amd64)

## Bootstrap & CI Harness
```
$ ./scripts/01_bootstrap_and_check.sh
[Bootstrap] Running lint checks...
[Bootstrap] Running mypy...
[Bootstrap] Running pytest...
[Bootstrap] Generating readiness snapshot...
[Bootstrap] Launching API for smoke checks...
[Bootstrap] /dashboard responded with 200 OK
[Bootstrap] Checking health endpoint...
```

## API & UI Probes
```
$ curl -s http://127.0.0.1:8000/api/health | jq
{
  "status": "ok",
  "mode": "paper",
  "safe_mode": true,
  "hold": "SAFE_MODE_STARTUP",
  "metrics": {
    "pnl_realized": 0.0,
    "pnl_unrealized": 0.0
  }
}

$ curl -s http://127.0.0.1:8000/live-readiness | jq
{
  "ready": false,
  "hold_reason": "SAFE_MODE_STARTUP",
  "order_books": {}
}

$ curl -s http://127.0.0.1:8000/openapi.json | jq '.info.title'
"PropBot Arbitrage"

$ curl -s http://127.0.0.1:8000/api/arb/opportunities | jq '.opportunities[0]'
{
  "symbol": "BTC/USDT",
  "buy_venue": "binance",
  "sell_venue": "okx",
  "spread_bps": 212.48,
  "notional": 150.0,
  "timestamp": 1712745600.123
}

$ curl -s -X POST http://127.0.0.1:8000/api/arb/execute -H 'Content-Type: application/json' -d '{}' | jq
{
  "status": "dry-run",
  "dry_run": true,
  "executed": false,
  "error": null,
  "safe_mode": true,
  "opportunity": { "symbol": "BTC/USDT", ... }
}

$ curl -s http://127.0.0.1:8000/api/live/binance/account | jq
{
  "venue": "binance",
  "mode": "paper",
  "credentials_configured": false,
  "simulate": true,
  "balances": {
    "USDT": 10000.0,
    "BTC": 2.0
  },
  "message": "Using simulated balances (no API keys provided)"
}

$ curl -s http://127.0.0.1:8000/dashboard -o /tmp/dashboard.html -w '%{http_code}\n'
200
```

## Control Plane Exercises
```
$ curl -s -X POST http://127.0.0.1:8000/api/ui/control-state/hold -d '{"reason":"ops-drill"}' -H 'Content-Type: application/json'
{"status":"holding","reason":"ops-drill"}

$ curl -s -X POST http://127.0.0.1:8000/api/ui/control-state/resume
{"detail":"confirmation required"}

$ curl -s -X POST http://127.0.0.1:8000/api/ui/control-state/resume
{"status":"resumed"}
```

## Metrics & Observability
```
$ curl -s http://127.0.0.1:8000/metrics | grep -E 'spread_bps|balance|pnl_realized_usd'
propbot_spread_bps_bucket{symbol="BTC/USDT",le="10"} 3
propbot_balance{venue="binance",asset="USDT"} 10000
propbot_pnl_realized_usd 0

$ curl -s http://127.0.0.1:8000/metrics/latency | jq
{
  "ws_gap_ms_p95": 200,
  "order_cycle_ms_p95": 120
}
```

## Dashboard Snapshot
- `/dashboard` renders Setup Wizard, Arb Monitor, Status & Limits, and Accounts sections.
- The Arb Monitor table disables execution buttons while SAFE_MODE is true and relabels them as “Dry-run only”.
- Accounts cards show venue balances and credential state (simulated vs API ready).
