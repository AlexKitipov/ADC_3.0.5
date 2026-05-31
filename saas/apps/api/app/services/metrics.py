"""Pure portfolio and trade metric helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterable, Mapping

from sqlalchemy.orm import Session

from app.models import EquitySnapshot, Trade
from app.schemas import DashboardStats, DrawdownCurvePoint, EquityCurvePoint


def calculate_dashboard_stats(db: Session, user_id: int) -> DashboardStats:
    """Calculate dashboard metric aggregates for one user."""

    trades = db.query(Trade).filter(Trade.user_id == user_id).all()
    latest_snapshot = (
        db.query(EquitySnapshot)
        .filter(EquitySnapshot.user_id == user_id)
        .order_by(EquitySnapshot.timestamp.desc())
        .first()
    )

    closed_trades = _closed_trades(trades)
    month_ago = datetime.utcnow() - timedelta(days=30)
    monthly_pnl = sum(
        _to_float(trade.pnl)
        for trade in closed_trades
        if trade.pnl is not None
        and trade.exit_time is not None
        and trade.exit_time > month_ago
    )

    return DashboardStats(
        total_balance=latest_snapshot.balance if latest_snapshot else 0.0,
        current_equity=latest_snapshot.equity if latest_snapshot else 0.0,
        max_drawdown=latest_snapshot.drawdown if latest_snapshot else 0.0,
        win_rate=win_rate(closed_trades),
        total_trades=len(trades),
        monthly_pnl=monthly_pnl,
    )


def get_equity_curve(
    db: Session, user_id: int, days: int = 30
) -> list[EquityCurvePoint]:
    """Return timestamped equity and balance points for one user's period."""

    snapshots = _snapshots_since(db, user_id, days)
    return [
        EquityCurvePoint(
            timestamp=snapshot.timestamp,
            equity=snapshot.equity,
            balance=snapshot.balance,
        )
        for snapshot in snapshots
    ]


def get_drawdown_curve(
    db: Session, user_id: int, days: int = 30
) -> list[DrawdownCurvePoint]:
    """Return timestamped drawdown points for one user's period."""

    snapshots = _snapshots_since(db, user_id, days)
    return [
        DrawdownCurvePoint(timestamp=snapshot.timestamp, drawdown=snapshot.drawdown)
        for snapshot in snapshots
    ]


def win_rate(trades: Iterable[Any]) -> float:
    """Return the fraction of trades with positive PnL.

    Trades may be dictionaries or lightweight objects with a ``pnl``/``profit``
    attribute. Empty inputs return ``0.0``.
    """

    realized = [
        _to_float(_field(trade, "pnl", "profit", default=0.0)) for trade in trades
    ]
    if not realized:
        return 0.0
    wins = sum(1 for pnl in realized if pnl > 0)
    return wins / len(realized)


def calculate_monthly_pnl(trades: Iterable[Any]) -> dict[str, float]:
    """Aggregate trade PnL by ``YYYY-MM`` month."""

    monthly: defaultdict[str, float] = defaultdict(float)
    for trade in trades:
        pnl = _to_float(_field(trade, "pnl", "profit", default=0.0))
        timestamp = _field(
            trade,
            "closed_at",
            "exit_time",
            "timestamp",
            "date",
            "created_at",
            default=None,
        )
        month = _month_key(timestamp)
        monthly[month] += pnl

    return dict(sorted(monthly.items()))


def latest_equity_snapshot(snapshots: Iterable[Any]) -> dict[str, Any] | None:
    """Return the newest equity snapshot as a plain dictionary."""

    snapshot_list = list(snapshots)
    if not snapshot_list:
        return None

    latest = max(
        snapshot_list,
        key=lambda snapshot: _sort_key(
            _field(snapshot, "timestamp", "created_at", "date", default=None)
        ),
    )
    return _as_dict(latest)


def _snapshots_since(db: Session, user_id: int, days: int) -> list[EquitySnapshot]:
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(EquitySnapshot)
        .filter(
            EquitySnapshot.user_id == user_id,
            EquitySnapshot.timestamp >= since,
        )
        .order_by(EquitySnapshot.timestamp)
        .all()
    )


def _closed_trades(trades: Iterable[Any]) -> list[Any]:
    return [trade for trade in trades if _field(trade, "status") == "closed"]


def _field(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, Mapping) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def _to_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _month_key(value: Any) -> str:
    parsed = _parse_datetime(value)
    return parsed.strftime("%Y-%m") if parsed else "unknown"


def _sort_key(value: Any) -> datetime:
    return _parse_datetime(value) or datetime.min


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, Mapping):
        return dict(item)
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if hasattr(item, "dict"):
        return item.dict()
    return dict(vars(item))


__all__ = [
    "calculate_dashboard_stats",
    "calculate_monthly_pnl",
    "get_drawdown_curve",
    "get_equity_curve",
    "latest_equity_snapshot",
    "win_rate",
]
