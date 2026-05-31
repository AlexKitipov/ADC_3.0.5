"""Tests for persisted signal generation API flow."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_and_login() -> str:
    """Register a unique user and return a bearer token."""

    suffix = uuid4().hex
    payload = {
        "email": f"{suffix}@example.com",
        "username": f"user_{suffix}",
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
    """Return authorization headers for the provided token."""

    return {"Authorization": f"Bearer {token}"}


def test_generate_signal_persists_default_settings_symbol_and_latest(
    monkeypatch,
) -> None:
    """Generated signal uses settings defaults and appears in latest signals."""

    monkeypatch.setenv("MARKET_DATA_PROVIDER", "mock")
    token = register_and_login()

    generate_response = client.post(
        "/api/v1/signals/generate",
        json={},
        headers=auth_headers(token),
    )
    latest_response = client.get(
        "/api/v1/signals/latest",
        headers=auth_headers(token),
    )

    assert generate_response.status_code == 200
    body = generate_response.json()
    assert body["signal"]["symbol"] == "EURUSD"
    assert body["signal"]["action"] in {"BUY", "SELL", "HOLD"}
    assert body["signal"]["price"] > 0
    assert body["decision"]["symbol"] == body["signal"]["symbol"]
    assert body["decision"]["action"] == body["signal"]["action"]
    assert body["decision"]["metadata"]["engine"] == "deterministic_rules_v1"
    assert latest_response.status_code == 200
    assert latest_response.json()[0]["id"] == body["signal"]["id"]


def test_generate_signal_accepts_symbol_timeframe_and_strategy_overrides(
    monkeypatch,
) -> None:
    """Request payload overrides configured user defaults for generation."""

    monkeypatch.setenv("MARKET_DATA_PROVIDER", "mock")
    token = register_and_login()

    generate_response = client.post(
        "/api/v1/signals/generate",
        json={
            "symbol": "gbpusd",
            "timeframe": "5min",
            "strategy_settings": {"rsi_period": 7, "macd_slow": 18},
        },
        headers=auth_headers(token),
    )
    symbol_response = client.get(
        "/api/v1/signals/by-symbol/GBPUSD",
        headers=auth_headers(token),
    )

    assert generate_response.status_code == 200
    body = generate_response.json()
    assert body["signal"]["symbol"] == "GBPUSD"
    assert body["decision"]["metadata"]["timeframe"] == "5min"
    assert symbol_response.status_code == 200
    assert [signal["id"] for signal in symbol_response.json()] == [body["signal"]["id"]]


def test_generate_signal_requires_authentication() -> None:
    """Signal generation is user-scoped and rejects anonymous callers."""

    response = client.post("/api/v1/signals/generate", json={})

    assert response.status_code == 401
