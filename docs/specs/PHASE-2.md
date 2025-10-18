# Phase-2: Dashboard MVP (cards + controls) + smoke tests

## Scope
- On `/` show cards:
  - Health (GET /api/health)
  - Readiness & order books (GET /live-readiness)
  - Last opportunities snapshot (GET /api/opportunities)
- Controls section:
  - Safe Mode ON/OFF  → POST /api/ui/control-state/safe-mode {"enabled": true|false}
  - HOLD / RESUME     → POST /api/ui/control-state/hold|resume
- Color badges (green OK, yellow safe_mode:true, red hold)
- Auto-refresh every 2s (fetch)
- Keep code small, no styling perfection.

## Acceptance
- Manual demo: `/` opens, cards render data, buttons work (status flips).
- Add 1–2 tiny tests for /api/ui/config/validate (valid + invalid).
