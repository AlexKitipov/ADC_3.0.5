"""Tests for dashboard metric service aggregation edge cases."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db import Base, SessionLocal, engine
from app.models import EquitySnapshot, Trade, User
from app.services.metrics import (
    calculate_dashboard_stats,
    get_drawdown_curve,
    get_equity_curve,
)


Base.metadata.create_all(bind=engine)


def create_user() -> User:
    """Persist and return a unique test user."""

    suffix = uuid4().hex
    db = SessionLocal()
    try:
        user = User(
            email=f"metrics_{suffix}@example.com",
            username=f"metrics_{suffix}",
            hashed_password="not-used",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user
    finally:
        db.close()


def test_dashboard_stats_default_when_user_has_no_trades_or_snapshots() -> None:
    user = create_user()
    db = SessionLocal()
    try:
        stats = calculate_dashboard_stats(db, user.id)
    finally:
        db.close()

    assert stats.total_balance == 0.0
    assert stats.current_equity == 0.0
    assert stats.max_drawdown == 0.0
    assert stats.win_rate == 0.0
    assert stats.total_trades == 0
    assert stats.monthly_pnl == 0.0


def test_dashboard_curves_return_empty_lists_when_user_has_no_snapshots() -> None:
    user = create_user()
    db = SessionLocal()
    try:
        equity_curve = get_equity_curve(db, user.id)
        drawdown_curve = get_drawdown_curve(db, user.id)
    finally:
        db.close()

    assert equity_curve == []
    assert drawdown_curve == []


def test_dashboard_stats_ignore_open_trades_for_realized_metrics() -> None:
    user = create_user()
    db = SessionLocal()
    try:
        db.add(
            Trade(
                user_id=user.id,
                symbol="BTCUSDT",
                entry_price=100.0,
                pnl=500.0,
                status="open",
            )
        )
        db.commit()

        stats = calculate_dashboard_stats(db, user.id)
    finally:
        db.close()

    assert stats.total_trades == 1
    assert stats.win_rate == 0.0
    assert stats.monthly_pnl == 0.0


def test_dashboard_stats_monthly_pnl_uses_only_recent_closed_trades() -> None:
    user = create_user()
    now = datetime.utcnow().replace(microsecond=0)
    db = SessionLocal()
    try:
        db.add_all(
            [
                EquitySnapshot(
                    user_id=user.id,
                    balance=10_000.0,
                    equity=10_075.0,
                    drawdown=0.015,
                    timestamp=now,
                ),
                Trade(
                    user_id=user.id,
                    symbol="BTCUSDT",
                    entry_price=100.0,
                    exit_price=110.0,
                    exit_time=now - timedelta(days=1),
                    pnl=100.0,
                    pnl_percent=0.1,
                    status="closed",
                ),
                Trade(
                    user_id=user.id,
                    symbol="ETHUSDT",
                    entry_price=100.0,
                    exit_price=95.0,
                    exit_time=now - timedelta(days=2),
                    pnl=-25.0,
                    pnl_percent=-0.05,
                    status="closed",
                ),
                Trade(
                    user_id=user.id,
                    symbol="SOLUSDT",
                    entry_price=100.0,
                    exit_price=125.0,
                    exit_time=now - timedelta(days=45),
                    pnl=50.0,
                    pnl_percent=0.25,
                    status="closed",
                ),
                Trade(
                    user_id=user.id,
                    symbol="ADAUSDT",
                    entry_price=100.0,
                    pnl=999.0,
                    status="open",
                ),
            ]
        )
        db.commit()

        stats = calculate_dashboard_stats(db, user.id)
    finally:
        db.close()

    assert stats.total_balance == 10_000.0
    assert stats.current_equity == 10_075.0
    assert stats.max_drawdown == 0.015
    assert stats.total_trades == 4
    assert stats.win_rate == pytest.approx(2 / 3)
    assert stats.monthly_pnl == 75.0


def test_dashboard_curves_are_ordered_and_filtered_by_requested_period() -> None:
    user = create_user()
    now = datetime.utcnow().replace(microsecond=0)
    old = now - timedelta(days=60)
    first = now - timedelta(days=2)
    second = now - timedelta(days=1)
    db = SessionLocal()
    try:
        db.add_all(
            [
                EquitySnapshot(
                    user_id=user.id,
                    balance=9_000.0,
                    equity=9_050.0,
                    drawdown=0.04,
                    timestamp=old,
                ),
                EquitySnapshot(
                    user_id=user.id,
                    balance=10_200.0,
                    equity=10_250.0,
                    drawdown=0.01,
                    timestamp=second,
                ),
                EquitySnapshot(
                    user_id=user.id,
                    balance=10_000.0,
                    equity=10_100.0,
                    drawdown=0.02,
                    timestamp=first,
                ),
            ]
        )
        db.commit()

        equity_curve = get_equity_curve(db, user.id, days=30)
        drawdown_curve = get_drawdown_curve(db, user.id, days=30)
    finally:
        db.close()

    assert [point.timestamp for point in equity_curve] == [first, second]
    assert [point.balance for point in equity_curve] == [10_000.0, 10_200.0]
    assert [point.equity for point in equity_curve] == [10_100.0, 10_250.0]
    assert [point.timestamp for point in drawdown_curve] == [first, second]
    assert [point.drawdown for point in drawdown_curve] == [0.02, 0.01]
