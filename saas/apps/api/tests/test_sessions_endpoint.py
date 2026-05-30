"""Tests for trading-session lifecycle endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_and_login() -> str:
    suffix = uuid4().hex
    payload = {
        "email": f"session_{suffix}@example.com",
        "username": f"session_{suffix}",
        "password": "correct-horse-battery-staple",
    }
    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def test_session_lifecycle_and_events_are_user_scoped() -> None:
    first_token = register_and_login()
    second_token = register_and_login()

    missing_current_response = client.get(
        "/api/v1/sessions/current", headers=auth_headers(first_token)
    )
    create_response = client.post(
        "/api/v1/sessions",
        json={
            "config": {
                "symbol": "BTCUSD",
                "initial_price": 100.0,
                "stream_interval": 0.1,
                "broker_error_rate": 0,
            }
        },
        headers=auth_headers(first_token),
    )
    session_id = create_response.json()["id"]
    other_user_response = client.get(
        "/api/v1/sessions/current", headers=auth_headers(second_token)
    )
    start_response = client.post(
        f"/api/v1/sessions/{session_id}/start", headers=auth_headers(first_token)
    )
    events_response = client.get(
        f"/api/v1/sessions/{session_id}/events", headers=auth_headers(first_token)
    )
    forbidden_events_response = client.get(
        f"/api/v1/sessions/{session_id}/events", headers=auth_headers(second_token)
    )
    stop_response = client.post(
        f"/api/v1/sessions/{session_id}/stop", headers=auth_headers(first_token)
    )

    assert missing_current_response.status_code == 404
    assert create_response.status_code == 201
    assert create_response.json()["status"] == "created"
    assert create_response.json()["symbol"] == "BTCUSD"
    assert other_user_response.status_code == 404
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert start_response.json()["broker_trade_allowed"] is True
    assert events_response.status_code == 200
    assert {event["type"] for event in events_response.json()} >= {
        "broker_connected",
        "session_started",
    }
    assert forbidden_events_response.status_code == 404
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"


def test_session_contract_is_documented_in_openapi() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    schemas = openapi["components"]["schemas"]
    assert {
        "SessionEventRead",
        "TradingSessionConfigSchema",
        "TradingSessionCreate",
        "TradingSessionState",
    }.issubset(schemas.keys())
    assert "/api/v1/sessions" in openapi["paths"]
    assert "/api/v1/sessions/current" in openapi["paths"]
    assert "/api/v1/sessions/{session_id}/start" in openapi["paths"]
    assert "/api/v1/sessions/{session_id}/stop" in openapi["paths"]
    assert "/api/v1/sessions/{session_id}/events" in openapi["paths"]
