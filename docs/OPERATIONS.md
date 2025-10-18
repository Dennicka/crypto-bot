# Operations Log & Procedures

## On-Call Rotation
- Week A: Trader A
- Week B: Trader B
- Escalation: call tree in shared ops doc.

## Incident Log Template
```
Date:
Severity:
Impact Summary:
Root Cause:
Resolution Steps:
Follow-up Actions:
```

## Compliance Checklist
- GDPR export handled via `/api/ui/stream` snapshot + journal export.
- Tax ledger derived from journal entries stored in SQLite.
- WORM export: copy journal DB to immutable storage daily.
- API credential hygiene: rotate Binance/OKX keys quarterly and update `.env` followed by `./validate_env.sh`.
