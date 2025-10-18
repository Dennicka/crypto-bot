from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from propbot.api.server import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_validate_ok(client: TestClient) -> None:
    payload = {
        "safe_mode": {"enabled": False, "require_double_confirmation": False},
        "engine": {
            "auto_trade": True,
            "min_spread_bps": 7,
            "cooldown_s": 2,
            "notional": 150,
            "max_open_trades": 1,
        },
    }
    response = client.post("/api/ui/config/validate", json=payload)
    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


def test_validate_errors(client: TestClient) -> None:
    payload = {"engine": {"min_spread_bps": -1, "cooldown_s": 0, "notional": 0, "max_open_trades": -2}}
    response = client.post("/api/ui/config/validate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    paths = {error["path"] for error in body["errors"]}
    assert "engine.min_spread_bps" in paths
    assert "engine.cooldown_s" in paths
    assert "engine.notional" in paths
    assert "engine.max_open_trades" in paths
