from __future__ import annotations

from fastapi.testclient import TestClient

from propbot.api.server import create_app


def test_dashboard_renders_keywords() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/html")
    body = response.text
    for keyword in ["Health", "Readiness", "Opportunities", "Controls", "Safe mode", "Hold", "Resume"]:
        assert keyword in body
