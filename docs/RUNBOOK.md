# PropBot Runbook

## Startup Checklist
1. Ensure `.env` secrets are loaded and validated via `./validate_env.sh`.
2. Review SAFE_MODE gates: system should boot in HOLD until confirmed.
3. Run `./scripts/01_bootstrap_and_check.sh` to confirm lint/tests pass and `/dashboard` responds 200.
4. Start the service with `python main.py run --config <config>` and open `http://localhost:8000/dashboard`.

## Hold / Resume Procedure
- Trigger HOLD: `curl -X POST http://localhost:8000/api/ui/control-state/hold -d '{"reason":"manual"}'`.
- Resume requires two invocations of `/resume` when SAFE_MODE enabled.

## Incident Response
- Inspect `/metrics` and `/metrics/latency` for SLO breaches.
- Use `/api/ui/recon/*` endpoints to confirm balances and positions.
- Record RCA in `docs/OPERATIONS.md` under the incident log section.

## DR Drills
- Simulate failure by stopping the service; verify restart completes within RTO.
- Confirm journal replay by checking new entries in `data/*_journal.sqlite3`.
