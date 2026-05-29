"""Tests for user settings API contracts and defaults."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import default_user_settings_values

client = TestClient(app)


def register_and_login() -> str:
    """Create a unique user and return an access token."""

    suffix = uuid4().hex
    payload = {
        "email": f"settings_{suffix}@example.com",
        "username": f"settings_{suffix}",
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


def auth_headers(token: str) -> dict[str, str]:
    """Return bearer token headers for authenticated settings requests."""

    return {"Authorization": f"Bearer {token}"}


def test_user_settings_get_creates_persisted_backend_defaults() -> None:
    token = register_and_login()

    response = client.get("/api/v1/settings/user-settings", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["id"], int)
    assert {key: body[key] for key in default_user_settings_values()} == {
        **default_user_settings_values(),
        "symbols": ["EURUSD", "GBPUSD"],
    }


def test_put_user_settings_requires_complete_replacement_payload() -> None:
    token = register_and_login()

    response = client.put(
        "/api/v1/settings/user-settings",
        headers=auth_headers(token),
        json={"risk_per_trade": 0.03},
    )

    assert response.status_code == 422


def test_put_user_settings_replaces_and_returns_response_model_with_id() -> None:
    token = register_and_login()
    payload = {
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "timeframe": "1h",
        "balance": 25000.0,
        "risk_per_trade": 0.03,
        "grid_levels": 5,
        "grid_step_pct": 0.01,
        "martingale_factor": 1.25,
        "enable_trading": True,
        "email_notifications": False,
    }

    response = client.put(
        "/api/v1/settings/user-settings",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["id"], int)
    assert {key: body[key] for key in payload} == payload

    get_response = client.get(
        "/api/v1/settings/user-settings", headers=auth_headers(token)
    )
    assert get_response.status_code == 200
    assert get_response.json() == body


def test_put_user_settings_rejects_response_only_id_field() -> None:
    token = register_and_login()
    payload = {
        "id": 123,
        "symbols": ["BTCUSDT"],
        "timeframe": "1h",
        "balance": 25000.0,
        "risk_per_trade": 0.03,
        "grid_levels": 5,
        "grid_step_pct": 0.01,
        "martingale_factor": 1.25,
        "enable_trading": True,
        "email_notifications": False,
    }

    response = client.put(
        "/api/v1/settings/user-settings",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422
