"""Programmable smoke test for the authenticated MVP API flow."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import EquitySnapshot, Signal, User
from tests.factories import auth_headers, unique_user_payload, user_settings_payload


@pytest.fixture()
def smoke_db(tmp_path: Path) -> Generator[sessionmaker[Session], None, None]:
    """Create an isolated SQLite database for the smoke scenario."""

    database_path = tmp_path / "mvp_smoke.sqlite3"
    engine = create_engine(
        f"sqlite:///{database_path}", connect_args={"check_same_thread": False}
    )
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    try:
        yield testing_session_local
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(
    smoke_db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    """Return a TestClient wired to the smoke DB and mock market data provider."""

    monkeypatch.setenv("MARKET_DATA_PROVIDER", "mock")

    def override_get_db() -> Generator[Session, None, None]:
        db = smoke_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_mvp_smoke_flow_register_login_settings_signal_dashboard_trades(
    client: TestClient, smoke_db: sessionmaker[Session]
) -> None:
    """Prove the MVP API can execute the core authenticated product journey."""

    registration_payload = unique_user_payload("mvp-smoke")
    register_response = client.post("/api/v1/auth/register", json=registration_payload)
    assert register_response.status_code == 201
    assert register_response.json()["username"] == registration_payload["username"]

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": registration_payload["username"],
            "password": registration_payload["password"],
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = auth_headers(token)

    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == registration_payload["email"]

    default_settings_response = client.get(
        "/api/v1/settings/user-settings", headers=headers
    )
    assert default_settings_response.status_code == 200
    default_settings = default_settings_response.json()
    assert default_settings["symbols"] == ["EURUSD", "GBPUSD"]
    assert default_settings["timeframe"] == "1d"
    assert default_settings["enable_trading"] is False

    updated_settings = user_settings_payload(
        symbols=["BTCUSD", "ETHUSD"],
        balance=25_000.0,
        enable_trading=True,
    )
    update_settings_response = client.put(
        "/api/v1/settings/user-settings", json=updated_settings, headers=headers
    )
    assert update_settings_response.status_code == 200
    assert update_settings_response.json()["symbols"] == ["BTCUSD", "ETHUSD"]
    assert update_settings_response.json()["balance"] == 25_000.0

    generate_signal_response = client.post(
        "/api/v1/signals/generate",
        json={"symbol": "BTCUSD", "timeframe": "1d", "strategy_settings": {}},
        headers=headers,
    )
    assert generate_signal_response.status_code == 200
    generated_signal = generate_signal_response.json()["signal"]
    assert generated_signal["symbol"] == "BTCUSD"
    assert generated_signal["action"] in {"BUY", "SELL", "HOLD"}

    latest_signals_response = client.get("/api/v1/signals/latest", headers=headers)
    assert latest_signals_response.status_code == 200
    assert [signal["id"] for signal in latest_signals_response.json()] == [
        generated_signal["id"]
    ]

    with smoke_db() as db:
        user = db.query(User).filter_by(username=registration_payload["username"]).one()
        assert db.query(Signal).filter_by(user_id=user.id).count() == 1
        db.add(
            EquitySnapshot(
                user_id=user.id,
                balance=25_000.0,
                equity=25_125.0,
                drawdown=0.01,
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()

    initial_dashboard_response = client.get("/api/v1/dashboard/stats", headers=headers)
    assert initial_dashboard_response.status_code == 200
    assert initial_dashboard_response.json() == {
        "total_balance": 25_000.0,
        "current_equity": 25_125.0,
        "max_drawdown": 0.01,
        "win_rate": 0.0,
        "total_trades": 0,
        "monthly_pnl": 0.0,
    }

    open_trade_response = client.post(
        "/api/v1/trades/open",
        json={"symbol": "BTCUSD", "entry_price": 100.0},
        headers=headers,
    )
    assert open_trade_response.status_code == 200
    open_trade = open_trade_response.json()
    assert open_trade["symbol"] == "BTCUSD"
    assert open_trade["status"] == "open"

    open_trades_response = client.get("/api/v1/trades/open", headers=headers)
    assert open_trades_response.status_code == 200
    assert [trade["id"] for trade in open_trades_response.json()] == [open_trade["id"]]

    close_trade_response = client.post(
        f"/api/v1/trades/close/{open_trade['id']}",
        json={"exit_price": 112.0},
        headers=headers,
    )
    assert close_trade_response.status_code == 200
    closed_trade = close_trade_response.json()
    assert closed_trade["status"] == "closed"
    assert closed_trade["pnl"] == 12.0
    assert closed_trade["pnl_percent"] == 12.0

    closed_trades_response = client.get("/api/v1/trades/closed", headers=headers)
    assert closed_trades_response.status_code == 200
    assert [trade["id"] for trade in closed_trades_response.json()] == [
        open_trade["id"]
    ]

    final_dashboard_response = client.get("/api/v1/dashboard/stats", headers=headers)
    assert final_dashboard_response.status_code == 200
    assert final_dashboard_response.json()["total_trades"] == 1
    assert final_dashboard_response.json()["win_rate"] == 1.0
    assert final_dashboard_response.json()["monthly_pnl"] == 12.0
