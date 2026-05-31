"""Focused onboarding-default tests for user settings."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import User, UserSettings, default_user_settings_values

client = TestClient(app)


def register_and_login() -> tuple[str, str]:
    """Create a unique user and return username plus access token."""

    suffix = uuid4().hex
    payload = {
        "email": f"settings_defaults_{suffix}@example.com",
        "username": f"settings_defaults_{suffix}",
        "password": "correct-horse-battery-staple",
    }

    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    return payload["username"], login_response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    """Return bearer token headers for authenticated settings requests."""

    return {"Authorization": f"Bearer {token}"}


def test_get_user_settings_returns_usable_defaults_without_existing_record() -> None:
    username, token = register_and_login()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).one()
        assert db.query(UserSettings).filter(UserSettings.user_id == user.id).first() is None
    finally:
        db.close()

    response = client.get("/api/v1/settings/user-settings", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["id"], int)
    assert {key: body[key] for key in default_user_settings_values()} == {
        **default_user_settings_values(),
        "symbols": ["EURUSD", "GBPUSD"],
    }


def test_dashboard_stats_do_not_require_saved_user_settings() -> None:
    _username, token = register_and_login()

    response = client.get("/api/v1/dashboard/stats", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["total_balance"] == 0.0


def test_put_user_settings_normalizes_symbols_and_persists_for_current_user() -> None:
    _username, token = register_and_login()
    payload = {
        "symbols": [" eurusd ", "EURUSD", "gbpusd"],
        "timeframe": "15m",
        "balance": 15000.0,
        "risk_per_trade": 0.01,
        "grid_levels": 4,
        "grid_step_pct": 0.0075,
        "martingale_factor": 1.2,
        "enable_trading": False,
        "email_notifications": True,
    }

    put_response = client.put(
        "/api/v1/settings/user-settings",
        headers=auth_headers(token),
        json=payload,
    )
    get_response = client.get(
        "/api/v1/settings/user-settings", headers=auth_headers(token)
    )

    assert put_response.status_code == 200
    assert put_response.json()["symbols"] == ["EURUSD", "GBPUSD"]
    assert get_response.status_code == 200
    assert get_response.json() == put_response.json()


def test_put_user_settings_validates_symbols_timeframe_risk_and_balance() -> None:
    _username, token = register_and_login()
    valid_payload = {
        "symbols": ["EURUSD"],
        "timeframe": "1h",
        "balance": 10000.0,
        "risk_per_trade": 0.02,
        "grid_levels": 3,
        "grid_step_pct": 0.005,
        "martingale_factor": 1.1,
        "enable_trading": False,
        "email_notifications": True,
    }

    invalid_payloads = [
        {**valid_payload, "symbols": []},
        {**valid_payload, "symbols": ["   "]},
        {**valid_payload, "timeframe": "2h"},
        {**valid_payload, "risk_per_trade": 0.0},
        {**valid_payload, "risk_per_trade": 0.5},
        {**valid_payload, "balance": -1.0},
    ]

    for payload in invalid_payloads:
        response = client.put(
            "/api/v1/settings/user-settings",
            headers=auth_headers(token),
            json=payload,
        )
        assert response.status_code == 422
