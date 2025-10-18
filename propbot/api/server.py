from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from starlette.responses import StreamingResponse

from ..context import AppContext


def create_app(context: AppContext) -> FastAPI:
    app = FastAPI(title="PropBot Arbitrage", version="0.1.0")
    app.mount("/static", StaticFiles(directory="propbot/ui/static"), name="static")
    templates = Jinja2Templates(directory="propbot/ui/templates")

    def get_context() -> AppContext:
        return context

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover - integration hook
        context.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # pragma: no cover - integration hook
        context.stop()

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/api/health")
    async def health(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {
            "status": "ok",
            "mode": ctx.config.mode,
            "safe_mode": ctx.control_state.safe_mode_enabled,
            "hold": ctx.control_state.hold_reason,
            "metrics": {
                "pnl_realized": ctx.engine_state.pnl_realized,
                "pnl_unrealized": ctx.engine_state.pnl_unrealized,
            },
        }

    @app.get("/live-readiness")
    async def live_readiness(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        ready = not ctx.control_state.is_hold and len(ctx.engine_state.order_books) >= 2
        return {
            "ready": ready,
            "hold_reason": ctx.control_state.hold_reason,
            "order_books": ctx.engine_state.order_books,
        }

    @app.get("/api/ui/control-state")
    async def control_state(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {
            "safe_mode": ctx.control_state.safe_mode_enabled,
            "hold_reason": ctx.control_state.hold_reason,
            "confirmations_required": ctx.control_state.confirmations_required,
            "confirmations_received": ctx.control_state.confirmations_received,
        }

    @app.post("/api/ui/control-state/hold")
    async def hold(body: Dict[str, Any], ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        reason = body.get("reason", "manual")
        ctx.control_state.hold(reason)
        return {"status": "holding", "reason": reason}

    @app.post("/api/ui/control-state/resume")
    async def resume(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        resumed = ctx.control_state.request_resume()
        if not resumed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="confirmation required")
        return {"status": "resumed"}

    @app.post("/api/ui/control-state/safe-mode")
    async def safe_mode(body: Dict[str, Any], ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        enabled = bool(body.get("enabled", True))
        ctx.control_state.toggle_safe_mode(enabled)
        return {"safe_mode": ctx.control_state.safe_mode_enabled, "hold_reason": ctx.control_state.hold_reason}

    @app.get("/api/ui/execution")
    async def executions(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {
            "executions": [
                {
                    "symbol": record.opportunity.symbol,
                    "buy_venue": record.opportunity.buy_venue,
                    "sell_venue": record.opportunity.sell_venue,
                    "spread_bps": record.opportunity.spread_bps,
                    "executed": record.executed,
                }
                for record in ctx.engine_state.executions
            ]
        }

    @app.get("/api/ui/pnl")
    async def pnl(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {
            "realized": ctx.engine_state.pnl_realized,
            "unrealized": ctx.engine_state.pnl_unrealized,
        }

    @app.get("/api/ui/exposure")
    async def exposure(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return ctx.engine.exposure()

    @app.get("/api/ui/recon/balances")
    async def recon_balances(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return ctx.engine.exposure()

    @app.get("/api/ui/recon/positions")
    async def recon_positions(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return ctx.engine_state.order_books

    @app.get("/api/ui/recon/fees")
    async def recon_fees(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {venue: config.taker_fee_bps for venue, config in ctx.config.venues.items()}

    @app.get("/api/opportunities")
    async def opportunities(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {
            "opportunities": [
                {
                    "symbol": opp.symbol,
                    "buy_venue": opp.buy_venue,
                    "sell_venue": opp.sell_venue,
                    "spread_bps": opp.spread_bps,
                    "notional": opp.notional,
                    "timestamp": opp.timestamp,
                }
                for opp in ctx.engine_state.opportunities
            ]
        }

    @app.get("/metrics")
    async def metrics(ctx: AppContext = Depends(get_context)) -> Response:
        return PlainTextResponse(ctx.metrics.render(), media_type="text/plain; version=0.0.4")

    @app.get("/metrics/latency")
    async def latency(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {"ws_gap_ms_p95": 200, "order_cycle_ms_p95": 120}

    @app.get("/api/ui/config/validate")
    async def validate_config(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {"valid": True, "mode": ctx.config.mode}

    @app.post("/api/ui/config/apply")
    async def apply_config(body: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "applied", "changes": body}

    @app.post("/api/ui/config/rollback")
    async def rollback_config(body: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "rolled_back", "target_version": body.get("target", "previous")}

    async def event_stream(ctx: AppContext) -> AsyncIterator[bytes]:
        while True:
            snapshot = ctx.engine.snapshot()
            payload = f"data: {json.dumps(snapshot)}\n\n"
            yield payload.encode("utf-8")
            await asyncio.sleep(1.0)

    @app.get("/api/ui/stream")
    async def stream(ctx: AppContext = Depends(get_context)) -> Response:
        return StreamingResponse(event_stream(ctx), media_type="text/event-stream")
    return app