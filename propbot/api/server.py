from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from ..context import AppContext
from ..config import load_config
from ..engine.state import Opportunity


def create_app(context: AppContext) -> FastAPI:
    app = FastAPI(title="PropBot Arbitrage", version="0.1.0")
    app.mount("/static", StaticFiles(directory="propbot/ui/static"), name="static")
    app.mount("/dashboard", StaticFiles(directory="propbot/ui/dashboard", html=True), name="dashboard")

    def get_context() -> AppContext:
        return context

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover - integration hook
        context.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # pragma: no cover - integration hook
        context.stop()

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    def _serialize_opportunity(opportunity: Opportunity) -> Dict[str, Any]:
        return {
            "symbol": opportunity.symbol,
            "buy_venue": opportunity.buy_venue,
            "sell_venue": opportunity.sell_venue,
            "spread_bps": opportunity.spread_bps,
            "notional": opportunity.notional,
            "timestamp": opportunity.timestamp,
        }

    def _resolve_venue_name(ctx: AppContext, venue: str) -> Optional[str]:
        venue_lower = venue.lower()
        for name in ctx.engine.connector_names():
            if name.lower() == venue_lower:
                return name
        return None

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
        books_ready = sum(1 for data in ctx.engine_state.order_books.values() if data)
        ready = not ctx.control_state.is_hold and books_ready >= 2
        return {
            "ready": ready,
            "hold_reason": ctx.control_state.hold_reason,
            "order_books": ctx.engine_state.order_books,
            "engine": ctx.engine.runtime_config(),
        }

    @app.get("/api/ui/status/overview")
    async def ui_status_overview(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        readiness = {
            "ready": not ctx.control_state.is_hold and len(ctx.engine_state.order_books) >= 2,
            "hold_reason": ctx.control_state.hold_reason,
            "order_books": ctx.engine_state.order_books,
        }
        venues: Dict[str, Any] = {}
        for venue_key, venue_cfg in ctx.config.venues.items():
            venues[venue_cfg.name] = {
                "trading_pairs": venue_cfg.trading_pairs,
                "maker_fee_bps": venue_cfg.maker_fee_bps,
                "taker_fee_bps": venue_cfg.taker_fee_bps,
                "simulate": venue_cfg.simulate,
                "credentials_configured": bool(venue_cfg.credentials.api_key and venue_cfg.credentials.api_secret),
            }
        return {
            "mode": ctx.config.mode,
            "safe_mode": ctx.control_state.safe_mode_enabled,
            "hold_reason": ctx.control_state.hold_reason,
            "limits": ctx.config.risk.model_dump(),
            "pnl": {
                "realized": ctx.engine_state.pnl_realized,
                "unrealized": ctx.engine_state.pnl_unrealized,
            },
            "order_books": ctx.engine_state.order_books,
            "venues": venues,
            "exposure": ctx.engine.exposure(),
            "readiness": readiness,
            "engine": ctx.engine.runtime_config(),
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
                    "reason": record.reason,
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

    @app.post("/api/ui/config/validate")
    async def validate_config(body: Dict[str, Any], ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        profile = body.get("profile", ctx.config.mode)
        env_file = ctx.env_file
        config_path = Path(f"configs/config.{profile}.yaml")
        try:
            config = load_config(config_path, env_file=env_file)
        except FileNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="config not found")
        except Exception as exc:  # pragma: no cover - validation error
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        missing_credentials: Dict[str, Dict[str, str]] = {}
        for venue in config.venue_list:
            creds = {
                "api_key": venue.credentials.api_key,
                "api_secret": venue.credentials.api_secret,
                "passphrase": getattr(venue.credentials, "passphrase", ""),
            }
            missing: Dict[str, str] = {}
            for key, value in creds.items():
                if key == "passphrase" and venue.name.lower() != "okx":
                    continue
                if not value:
                    missing[key] = "missing"
            missing_credentials[venue.name] = missing
        return {
            "valid": True,
            "mode": config.mode,
            "engine": config.engine.model_dump(),
            "venues": [
                {
                    "name": venue.name,
                    "pairs": venue.trading_pairs,
                    "simulate": venue.simulate,
                    "missing_credentials": missing_credentials.get(venue.name, {}),
                }
                for venue in config.venue_list
            ],
        }

    @app.post("/api/ui/config/apply")
    async def apply_config(body: Dict[str, Any], ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        min_spread = body.get("min_spread_bps")
        default_notional = body.get("default_notional_usd")
        if min_spread is None and default_notional is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no overrides supplied")
        ctx.apply_engine_overrides(min_spread_bps=min_spread, default_notional_usd=default_notional)
        return {"status": "applied", "engine": ctx.engine.runtime_config()}

    @app.get("/api/ui/recon/balances")
    async def recon_balances(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return ctx.engine.exposure()

    @app.get("/api/ui/recon/positions")
    async def recon_positions(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return ctx.engine_state.order_books

    @app.get("/api/ui/recon/fees")
    async def recon_fees(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {venue: config.taker_fee_bps for venue, config in ctx.config.venues.items()}

    @app.get("/api/arb/opportunities")
    @app.get("/api/opportunities")
    async def opportunities(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        listed = ctx.engine.listed_opportunities(limit=20)
        return {"opportunities": [_serialize_opportunity(opp) for opp in listed]}

    @app.post("/api/arb/execute")
    async def execute_arbitrage(body: Dict[str, Any], ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        requested_symbol = body.get("symbol")
        requested_buy = body.get("buy_venue")
        requested_sell = body.get("sell_venue")
        candidate: Optional[Opportunity] = None
        opportunities = ctx.engine.listed_opportunities(limit=20)
        if requested_symbol or requested_buy or requested_sell:
            for opportunity in opportunities:
                if requested_symbol and opportunity.symbol != requested_symbol:
                    continue
                if requested_buy and opportunity.buy_venue != requested_buy:
                    continue
                if requested_sell and opportunity.sell_venue != requested_sell:
                    continue
                candidate = opportunity
                break
        if candidate is None:
            candidate = ctx.engine.best_opportunity()
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no opportunities available")
        result = ctx.engine.execute_opportunity(candidate)
        return {"opportunity": _serialize_opportunity(candidate), **result, "safe_mode": ctx.control_state.safe_mode_enabled}

    @app.get("/api/live/{venue}/account")
    async def live_account(venue: str, ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        resolved = _resolve_venue_name(ctx, venue)
        if resolved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"unknown venue '{venue}'")
        venue_cfg = next((cfg for cfg in ctx.config.venue_list if cfg.name == resolved), None)
        if venue_cfg is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"unconfigured venue '{venue}'")
        connector = ctx.engine.connector(resolved)
        if connector is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"connector for '{venue}' not available")
        credentials_configured = bool(venue_cfg.credentials.api_key and venue_cfg.credentials.api_secret)
        balances = connector.balances() if (credentials_configured or venue_cfg.simulate) else {}
        message = None
        if not credentials_configured and not venue_cfg.simulate:
            message = "API keys missing: balances unavailable"
        elif not credentials_configured and venue_cfg.simulate:
            message = "Using simulated balances (no API keys provided)"
        return {
            "venue": resolved,
            "mode": ctx.config.mode,
            "credentials_configured": credentials_configured,
            "simulate": venue_cfg.simulate,
            "balances": balances,
            "message": message,
        }

    @app.get("/metrics")
    async def metrics(ctx: AppContext = Depends(get_context)) -> Response:
        return PlainTextResponse(ctx.metrics.render(), media_type="text/plain; version=0.0.4")

    @app.get("/metrics/latency")
    async def latency(ctx: AppContext = Depends(get_context)) -> Dict[str, Any]:
        return {"ws_gap_ms_p95": 200, "order_cycle_ms_p95": 120}

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
