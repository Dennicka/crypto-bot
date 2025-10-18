from fastapi.testclient import TestClient
from propbot.api.server import app

client = TestClient(app)

def test_validate_ok():
    payload = {
        "safe_mode": {"enabled": False, "require_double_confirmation": False},
        "engine": {"auto_trade": True, "min_spread_bps": 7, "cooldown_s": 2, "notional": 150, "max_open_trades": 1}
    }
    r = client.post("/api/ui/config/validate", json=payload)
    assert r.status_code == 200
    assert r.json() == {"valid": True}

def test_validate_errors():
    payload = {"engine": {"min_spread_bps": -1, "cooldown_s": 0, "notional": 0, "max_open_trades": -2}}
    r = client.post("/api/ui/config/validate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    paths = {e["path"] for e in body["errors"]}
    assert "engine.min_spread_bps" in paths
    assert "engine.cooldown_s" in paths
    assert "engine.notional" in paths
    assert "engine.max_open_trades" in paths
