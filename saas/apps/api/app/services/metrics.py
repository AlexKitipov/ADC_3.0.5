"""Pure portfolio and trade metric helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping


def win_rate(trades: Iterable[Any]) -> float:
    """Return the fraction of trades with positive PnL.

    Trades may be dictionaries or lightweight objects with a ``pnl``/``profit``
    attribute. Empty inputs return ``0.0``.
    """

    realized = [_to_float(_field(trade, "pnl", "profit", default=0.0)) for trade in trades]
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


__all__ = ["calculate_monthly_pnl", "latest_equity_snapshot", "win_rate"]
