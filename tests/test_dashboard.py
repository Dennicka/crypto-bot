from fastapi.testclient import TestClient
from propbot.api.server import app

client = TestClient(app)

def test_dashboard_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert b"PropBot" in r.content
