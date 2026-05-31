"""MVP contract tests for persisted trade-history endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.broker.mock_broker import MockBrokerAPI

client = TestClient(app)


def register_and_login(prefix: str = "trades-mvp") -> str:
    """Register a unique test user and return a bearer token."""

    suffix = uuid4().hex
    payload = {
        "email": f"{prefix}-{suffix}@example.com",
        "username": f"{prefix}_{suffix}",
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


def test_trade_history_open_close_flow_is_persisted_and_user_scoped(monkeypatch) -> None:
    """Open and close trades through /trades without touching broker execution."""

    def fail_broker_order(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("/trades must not execute broker orders directly")

    monkeypatch.setattr(MockBrokerAPI, "send_order", fail_broker_order)
    first_token = register_and_login("trades-mvp-first")
    second_token = register_and_login("trades-mvp-second")

    open_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "btcusd", "entry_price": 100.0},
        headers=auth_headers(first_token),
    )
    assert open_response.status_code == 200
    trade = open_response.json()
    trade_id = trade["id"]
    assert trade["symbol"] == "BTCUSD"
    assert trade["status"] == "open"
    assert trade["exit_price"] is None
    assert trade["pnl"] is None

    owner_open_response = client.get(
        "/api/v1/trades/open", headers=auth_headers(first_token)
    )
    other_open_response = client.get(
        "/api/v1/trades/open", headers=auth_headers(second_token)
    )
    other_close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 110.0},
        headers=auth_headers(second_token),
    )

    assert owner_open_response.status_code == 200
    assert [item["id"] for item in owner_open_response.json()] == [trade_id]
    assert other_open_response.status_code == 200
    assert other_open_response.json() == []
    assert other_close_response.status_code == 404

    close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 112.0},
        headers=auth_headers(first_token),
    )
    assert close_response.status_code == 200
    closed_trade = close_response.json()
    assert closed_trade["id"] == trade_id
    assert closed_trade["status"] == "closed"
    assert closed_trade["exit_price"] == 112.0
    assert closed_trade["exit_time"] is not None
    assert closed_trade["pnl"] == 12.0
    assert closed_trade["pnl_percent"] == 12.0

    open_after_close_response = client.get(
        "/api/v1/trades/open", headers=auth_headers(first_token)
    )
    closed_history_response = client.get(
        "/api/v1/trades/closed", headers=auth_headers(first_token)
    )

    assert open_after_close_response.status_code == 200
    assert open_after_close_response.json() == []
    assert closed_history_response.status_code == 200
    assert [item["id"] for item in closed_history_response.json()] == [trade_id]


def test_trade_close_contract_rejects_invalid_and_duplicate_closes() -> None:
    """The close endpoint requires a JSON body and only closes an open trade once."""

    token = register_and_login("trades-mvp-contract")
    invalid_open_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "ETHUSD", "entry_price": 0},
        headers=auth_headers(token),
    )
    open_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "ETHUSD", "entry_price": 50.0},
        headers=auth_headers(token),
    )
    trade_id = open_response.json()["id"]

    query_close_response = client.post(
        f"/api/v1/trades/close/{trade_id}?exit_price=45.0",
        headers=auth_headers(token),
    )
    close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 45.0},
        headers=auth_headers(token),
    )
    duplicate_close_response = client.post(
        f"/api/v1/trades/close/{trade_id}",
        json={"exit_price": 44.0},
        headers=auth_headers(token),
    )

    assert invalid_open_response.status_code == 422
    assert query_close_response.status_code == 422
    assert close_response.status_code == 200
    assert close_response.json()["pnl"] == -5.0
    assert close_response.json()["pnl_percent"] == -10.0
    assert duplicate_close_response.status_code == 409
    assert duplicate_close_response.json() == {"detail": "Trade is already closed"}


def test_trade_mvp_contract_is_documented_in_openapi() -> None:
    """OpenAPI documents stable trade-history collection/action endpoints."""

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/trades/open" in paths
    assert "/api/v1/trades/closed" in paths
    assert "/api/v1/trades/close/{trade_id}" in paths
    assert paths["/api/v1/trades/open"]["get"]["responses"]["200"]
    assert paths["/api/v1/trades/closed"]["get"]["parameters"][0]["name"] == "limit"
    assert paths["/api/v1/trades/open"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/TradeCreate"}
    assert paths["/api/v1/trades/close/{trade_id}"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"] == {"$ref": "#/components/schemas/TradeClose"}
