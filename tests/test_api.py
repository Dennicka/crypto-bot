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
