"""Dashboard metric and chart response schemas."""

from datetime import datetime

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Dashboard performance metrics."""

    total_balance: float
    current_equity: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    monthly_pnl: float


class EquityCurvePoint(BaseModel):
    """Single timestamped balance and equity point for dashboard charts."""

    timestamp: datetime
    equity: float
    balance: float


class DrawdownCurvePoint(BaseModel):
    """Single timestamped drawdown point for dashboard charts."""

    timestamp: datetime
    drawdown: float


__all__ = ["DashboardStats", "DrawdownCurvePoint", "EquityCurvePoint"]
