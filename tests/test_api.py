import asyncio
from pathlib import Path

import pytest
from httpx import AsyncClient

from propbot.api import create_app
from propbot.context import AppContext


@pytest.mark.asyncio
async def test_health_endpoint(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mode: paper
safe_mode:
  enabled: false
venues:
  binance:
    name: binance
    trading_pairs: ["BTC/USDT"]
  okx:
    name: okx
    trading_pairs: ["BTC/USDT"]
        """,
        encoding="utf-8",
    )
    context = AppContext.from_file(config_path)
    app = create_app(context)
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["mode"] == "paper"


@pytest.mark.asyncio
async def test_hold_resume_flow(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mode: paper
safe_mode:
  enabled: true
  hold_on_startup: true
venues:
  binance:
    name: binance
    trading_pairs: ["BTC/USDT"]
  okx:
    name: okx
    trading_pairs: ["BTC/USDT"]
        """,
        encoding="utf-8",
    )
    context = AppContext.from_file(config_path)
    app = create_app(context)
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.get("/api/ui/control-state")
        assert resp.json()["hold_reason"] == "SAFE_MODE_STARTUP"
        await client.post("/api/ui/control-state/resume")
        final = await client.post("/api/ui/control-state/resume")
        assert final.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_route_served(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mode: paper
safe_mode:
  enabled: true
venues:
  binance:
    name: binance
    trading_pairs: ["BTC/USDT"]
  okx:
    name: okx
    trading_pairs: ["BTC/USDT"]
        """,
        encoding="utf-8",
    )
    context = AppContext.from_file(config_path)
    app = create_app(context)
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/dashboard")
        assert response.status_code == 200
        assert "Arb Monitor" in response.text


@pytest.mark.asyncio
async def test_opportunities_and_execute_dry_run(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mode: paper
safe_mode:
  enabled: true
venues:
  binance:
    name: binance
    trading_pairs: ["BTC/USDT"]
  okx:
    name: okx
    trading_pairs: ["BTC/USDT"]
        """,
        encoding="utf-8",
    )
    context = AppContext.from_file(config_path)
    context.engine_state.order_books = {
        "binance": {"bid": 100.0, "ask": 101.0},
        "okx": {"bid": 103.0, "ask": 104.0},
    }
    app = create_app(context)
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        opportunities = await client.get("/api/arb/opportunities")
        assert opportunities.status_code == 200
        payload = opportunities.json()
        assert payload["opportunities"], "expected at least one opportunity"
        execute = await client.post("/api/arb/execute", json={})
        assert execute.status_code == 200
        result = execute.json()
        assert result["dry_run"] is True
        assert result["opportunity"]["symbol"] == "BTC/USDT"


@pytest.mark.asyncio
async def test_live_account_endpoint(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mode: paper
safe_mode:
  enabled: true
venues:
  binance:
    name: binance
    trading_pairs: ["BTC/USDT"]
    simulate: true
  okx:
    name: okx
    trading_pairs: ["BTC/USDT"]
    simulate: true
        """,
        encoding="utf-8",
    )
    context = AppContext.from_file(config_path)
    app = create_app(context)
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        account = await client.get("/api/live/binance/account")
        assert account.status_code == 200
        payload = account.json()
        assert payload["venue"] == "binance"
        assert payload["simulate"] is True
        assert "balances" in payload
