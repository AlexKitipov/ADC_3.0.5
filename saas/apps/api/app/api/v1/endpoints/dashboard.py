"""Dashboard API endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EquitySnapshot, Trade, User
from app.schemas import DashboardStats, DrawdownCurvePoint, EquityCurvePoint
from app.security import get_current_user

router = APIRouter()


@router.get("/summary")
def dashboard_summary() -> dict[str, str]:
    """Return dashboard service readiness."""

    return {"status": "dashboard-ready"}


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DashboardStats:
    """Return aggregate dashboard metrics for the current user."""

    trades = db.query(Trade).filter(Trade.user_id == current_user.id).all()
    latest_snapshot = (
        db.query(EquitySnapshot)
        .filter(EquitySnapshot.user_id == current_user.id)
        .order_by(EquitySnapshot.timestamp.desc())
        .first()
    )

    closed_trades = [trade for trade in trades if trade.status == "closed"]
    winning_trades = [
        trade for trade in closed_trades if trade.pnl is not None and trade.pnl > 0
    ]
    win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0

    month_ago = datetime.utcnow() - timedelta(days=30)
    monthly_pnl = sum(
        trade.pnl
        for trade in closed_trades
        if trade.pnl is not None
        and trade.exit_time is not None
        and trade.exit_time > month_ago
    )

    return DashboardStats(
        total_balance=latest_snapshot.balance if latest_snapshot else 0,
        current_equity=latest_snapshot.equity if latest_snapshot else 0,
        max_drawdown=latest_snapshot.drawdown if latest_snapshot else 0,
        win_rate=win_rate,
        total_trades=len(trades),
        monthly_pnl=monthly_pnl,
    )


@router.get("/equity-curve", response_model=list[EquityCurvePoint])
def get_equity_curve(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30,
) -> list[EquityCurvePoint]:
    """Return the user's equity and balance history for the requested period."""

    since = datetime.utcnow() - timedelta(days=days)
    snapshots = (
        db.query(EquitySnapshot)
        .filter(
            EquitySnapshot.user_id == current_user.id,
            EquitySnapshot.timestamp >= since,
        )
        .order_by(EquitySnapshot.timestamp)
        .all()
    )

    return [
        EquityCurvePoint(
            timestamp=snapshot.timestamp,
            equity=snapshot.equity,
            balance=snapshot.balance,
        )
        for snapshot in snapshots
    ]


@router.get("/drawdown-curve", response_model=list[DrawdownCurvePoint])
def get_drawdown_curve(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30,
) -> list[DrawdownCurvePoint]:
    """Return the user's drawdown history for the requested period."""

    since = datetime.utcnow() - timedelta(days=days)
    snapshots = (
        db.query(EquitySnapshot)
        .filter(
            EquitySnapshot.user_id == current_user.id,
            EquitySnapshot.timestamp >= since,
        )
        .order_by(EquitySnapshot.timestamp)
        .all()
    )

    return [
        DrawdownCurvePoint(timestamp=snapshot.timestamp, drawdown=snapshot.drawdown)
        for snapshot in snapshots
    ]
