"""Tests for authenticated signal, trade, and user settings endpoints."""

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


def test_signal_create_latest_and_symbol_filters_are_user_scoped() -> None:
    first_token = register_and_login()
    second_token = register_and_login()
    signal_payload = {
        "symbol": "EURUSD",
        "action": "BUY",
        "price": 1.085,
        "rsi": 44.2,
        "macd": 0.15,
    }

    create_response = client.post(
        "/api/v1/signals/create",
        json=signal_payload,
        headers=auth_headers(first_token),
    )
    second_user_response = client.get(
        "/api/v1/signals/latest", headers=auth_headers(second_token)
    )
    latest_response = client.get(
        "/api/v1/signals/latest", headers=auth_headers(first_token)
    )
    symbol_response = client.get(
        "/api/v1/signals/by-symbol/EURUSD", headers=auth_headers(first_token)
    )

    assert create_response.status_code == 200
    assert create_response.json()["symbol"] == "EURUSD"
    assert second_user_response.status_code == 200
    assert second_user_response.json() == []
    assert latest_response.status_code == 200
    assert [signal["symbol"] for signal in latest_response.json()] == ["EURUSD"]
    assert symbol_response.status_code == 200
    assert [signal["action"] for signal in symbol_response.json()] == ["BUY"]


def test_signal_create_rejects_unknown_action() -> None:
    token = register_and_login()

    create_response = client.post(
        "/api/v1/signals/create",
        json={
            "symbol": "EURUSD",
            "action": "STRONG_BUY",
            "price": 1.085,
            "rsi": 44.2,
            "macd": 0.15,
        },
        headers=auth_headers(token),
    )

    assert create_response.status_code == 422
    assert create_response.json()["detail"][0]["loc"] == ["body", "action"]


def test_trade_open_close_and_history_are_user_scoped() -> None:
    first_token = register_and_login()
    second_token = register_and_login()

    open_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "BTCUSD", "entry_price": 100.0},
        headers=auth_headers(first_token),
    )
    trade_id = open_response.json()["id"]
    other_user_open_response = client.get(
        "/api/v1/trades/open", headers=auth_headers(second_token)
    )
    close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 112.0},
        headers=auth_headers(first_token),
    )
    open_trades_response = client.get(
        "/api/v1/trades/open", headers=auth_headers(first_token)
    )
    closed_trades_response = client.get(
        "/api/v1/trades/closed", headers=auth_headers(first_token)
    )

    assert open_response.status_code == 200
    assert open_response.json()["status"] == "open"
    assert other_user_open_response.status_code == 200
    assert other_user_open_response.json() == []
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"
    assert close_response.json()["pnl"] == 12.0
    assert close_response.json()["pnl_percent"] == 12.0
    assert open_trades_response.status_code == 200
    assert open_trades_response.json() == []
    assert closed_trades_response.status_code == 200
    assert [trade["id"] for trade in closed_trades_response.json()] == [trade_id]


def test_close_trade_rejects_trades_owned_by_other_users() -> None:
    first_token = register_and_login()
    second_token = register_and_login()
    open_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "ETHUSD", "entry_price": 50.0},
        headers=auth_headers(first_token),
    )
    trade_id = open_response.json()["id"]

    close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 45.0},
        headers=auth_headers(second_token),
    )

    assert close_response.status_code == 404
    assert close_response.json() == {"detail": "Trade not found"}


def test_trade_open_and_close_contract_uses_json_request_bodies() -> None:
    token = register_and_login()

    invalid_open_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "BTCUSD", "entry_price": 0},
        headers=auth_headers(token),
    )
    open_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "btcusd", "entry_price": 100.0},
        headers=auth_headers(token),
    )
    trade_id = open_response.json()["id"]
    query_close_response = client.post(
        f"/api/v1/trades/close/{trade_id}?exit_price=112.0",
        headers=auth_headers(token),
    )
    close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 112.0},
        headers=auth_headers(token),
    )
    duplicate_close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 113.0},
        headers=auth_headers(token),
    )

    assert invalid_open_response.status_code == 422
    assert open_response.status_code == 200
    assert open_response.json()["symbol"] == "BTCUSD"
    assert query_close_response.status_code == 422
    assert close_response.status_code == 200
    assert close_response.json()["exit_price"] == 112.0
    assert duplicate_close_response.status_code == 409
    assert duplicate_close_response.json() == {"detail": "Trade is already closed"}


def test_trade_open_close_contract_is_documented_in_openapi() -> None:
    openapi_response = client.get("/openapi.json")

    assert openapi_response.status_code == 200
    openapi = openapi_response.json()
    schemas = openapi["components"]["schemas"]
    assert {"Trade", "TradeCreate", "TradeClose"}.issubset(schemas.keys())
    assert openapi["paths"]["/api/v1/trades/open"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/TradeCreate"}
    assert openapi["paths"]["/api/v1/trades/close/{trade_id}"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"] == {"$ref": "#/components/schemas/TradeClose"}


def test_user_settings_can_be_created_and_read() -> None:
    token = register_and_login()
    payload = {
        "symbols": ["EURUSD", "USDJPY"],
        "timeframe": "4h",
        "balance": 25000.0,
        "risk_per_trade": 0.01,
        "grid_levels": 5,
        "grid_step_pct": 0.0025,
        "martingale_factor": 1.05,
        "enable_trading": True,
        "email_notifications": False,
    }

    update_response = client.put(
        "/api/v1/settings/user-settings",
        json=payload,
        headers=auth_headers(token),
    )
    read_response = client.get(
        "/api/v1/settings/user-settings", headers=auth_headers(token)
    )

    assert update_response.status_code == 200
    assert update_response.json() == {"message": "Settings updated successfully"}
    assert read_response.status_code == 200
    body = read_response.json()
    assert body["symbols"] == ["EURUSD", "USDJPY"]
    assert body["timeframe"] == "4h"
    assert body["enable_trading"] is True
    assert body["email_notifications"] is False
