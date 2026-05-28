"""Smoke tests for the FastAPI application."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_router_is_available() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/signals")

    assert response.status_code == 200
    assert response.json() == {"signals": []}


def test_legacy_router_is_available() -> None:
    client = TestClient(app)

    response = client.get("/api/signals")

    assert response.status_code == 200
    assert response.json() == {"signals": []}
