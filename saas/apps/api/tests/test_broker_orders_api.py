"""Tests for broker-client backed order endpoints."""

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints import orders as orders_endpoint
from app.main import app
from app.services.broker.providers import get_broker_client
from app.services.order_management import ERR_INVALID_TICKET, ERR_NO_ERROR, OP_BUY

client = TestClient(app)


class FakeBrokerClient:
    """Small broker adapter proving endpoints depend on the BrokerClient API."""

    def __init__(self) -> None:
        self.orders: dict[int, dict] = {}
        self.last_error = ERR_NO_ERROR
        self.next_ticket = 700000

    def place_order(self, order):
        ticket = self.next_ticket
        self.next_ticket += 1
        self.orders[ticket] = {
            "ticket": ticket,
            "symbol": order.symbol.upper(),
            "cmd": OP_BUY,
            "volume": order.volume,
            "open_price": order.price,
            "sl": order.stop_loss,
            "tp": order.take_profit,
            "open_time": datetime(2026, 1, 1, 12, 0, 0),
            "status": "open",
        }
        return self.orders[ticket]

    def close_order(self, ticket, order_close):
        order = self.orders.get(ticket)
        if order is None:
            self.last_error = ERR_INVALID_TICKET
            return {"ticket": ticket, "status": "not_found"}
        order["status"] = "closed"
        order["close_price"] = order_close.price
        order["close_time"] = datetime(2026, 1, 1, 12, 5, 0)
        return order

    def get_open_orders(self):
        return [order for order in self.orders.values() if order["status"] == "open"]

    def get_account_snapshot(self):
        return {"provider": "fake", "open_orders": len(self.get_open_orders())}

    def get_order(self, ticket):
        return self.orders.get(ticket)

    def get_last_error(self):
        return self.last_error


def register_and_login() -> str:
    """Register a unique user and return a bearer token."""

    suffix = uuid4().hex
    payload = {
        "email": f"broker-{suffix}@example.com",
        "username": f"broker_{suffix}",
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


def test_orders_endpoints_use_broker_client_dependency() -> None:
    fake_broker = FakeBrokerClient()
    token = register_and_login()
    app.dependency_overrides[get_broker_client] = lambda: fake_broker
    orders_endpoint._order_owners.clear()

    try:
        create_response = client.post(
            "/api/v1/orders",
            json={
                "symbol": "eurusd",
                "order_type": "BUY",
                "volume": 0.1,
                "price": 1.0851,
                "slippage": 100,
            },
            headers=auth_headers(token),
        )
        ticket = create_response.json()["ticket"]
        get_response = client.get(
            f"/api/v1/orders/{ticket}", headers=auth_headers(token)
        )
        open_response = client.get("/api/v1/orders/open", headers=auth_headers(token))
        close_response = client.post(
            f"/api/v1/orders/{ticket}/close",
            json={"price": 1.0850, "slippage": 100},
            headers=auth_headers(token),
        )
    finally:
        app.dependency_overrides.pop(get_broker_client, None)
        orders_endpoint._order_owners.clear()

    assert create_response.status_code == 201
    assert create_response.json()["symbol"] == "EURUSD"
    assert get_response.status_code == 200
    assert get_response.json()["ticket"] == ticket
    assert open_response.status_code == 200
    assert [order["ticket"] for order in open_response.json()] == [ticket]
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"
