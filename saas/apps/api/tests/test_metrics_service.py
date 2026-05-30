"""Tests for pure metric helper functions."""

from dataclasses import dataclass
from datetime import datetime

from app.services.metrics import calculate_monthly_pnl, latest_equity_snapshot, win_rate


@dataclass
class EquitySnapshot:
    timestamp: datetime
    equity: float


def test_win_rate_handles_empty_and_profitable_trades() -> None:
    assert win_rate([]) == 0.0
    assert win_rate([{"pnl": 10}, {"pnl": -5}, {"pnl": 0}]) == 1 / 3


def test_calculate_monthly_pnl_groups_by_close_month() -> None:
    trades = [
        {"closed_at": "2026-01-15T10:00:00", "pnl": 10.5},
        {"closed_at": "2026-01-20T10:00:00", "pnl": -2.0},
        {"closed_at": "2026-02-01T10:00:00", "profit": 4.0},
    ]

    assert calculate_monthly_pnl(trades) == {"2026-01": 8.5, "2026-02": 4.0}


def test_latest_equity_snapshot_returns_newest_plain_dict() -> None:
    snapshots = [
        EquitySnapshot(timestamp=datetime(2026, 1, 1), equity=1000.0),
        EquitySnapshot(timestamp=datetime(2026, 1, 2), equity=1010.0),
    ]

    assert latest_equity_snapshot(snapshots) == {
        "timestamp": datetime(2026, 1, 2),
        "equity": 1010.0,
    }
    assert latest_equity_snapshot([]) is None
