"""Tests for ORM model registration and Pydantic schema behavior."""

from datetime import datetime

from app.db import Base
from app.models import UserSettings
from app.schemas import Trade, UserSettingsUpdate


def test_all_core_tables_are_registered() -> None:
    expected_tables = {
        "equity_snapshots",
        "signals",
        "trades",
        "user_settings",
        "users",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_user_settings_symbols_default_is_not_shared() -> None:
    first_default = UserSettings.__table__.c.symbols.default.arg()
    second_default = UserSettings.__table__.c.symbols.default.arg()

    first_default.append("USDJPY")

    assert second_default == ["EURUSD", "GBPUSD"]


def test_trade_schema_validates_optional_exit_fields() -> None:
    trade = Trade(
        id=1,
        symbol="EURUSD",
        entry_price=1.085,
        exit_price=None,
        entry_time=datetime(2026, 5, 28, 12, 0, 0),
        exit_time=None,
        pnl=None,
        pnl_percent=None,
        status="open",
    )

    assert trade.model_dump()["status"] == "open"


def test_user_settings_update_schema_uses_builtin_generics() -> None:
    payload = UserSettingsUpdate(
        symbols=["EURUSD", "GBPUSD"],
        timeframe="1d",
        balance=10000.0,
        risk_per_trade=0.02,
        grid_levels=3,
        grid_step_pct=0.005,
        martingale_factor=1.1,
        enable_trading=False,
        email_notifications=True,
    )

    assert payload.symbols == ["EURUSD", "GBPUSD"]
