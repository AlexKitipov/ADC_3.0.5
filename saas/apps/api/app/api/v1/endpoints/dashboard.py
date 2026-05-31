"""Dashboard API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import DashboardStats, DrawdownCurvePoint, EquityCurvePoint
from app.security import get_current_user
from app.services import metrics as metrics_service

router = APIRouter()


@router.get(
    "/summary",
    tags=["Readiness / Demo"],
    summary="Readiness-only dashboard wiring marker",
)
def dashboard_summary() -> dict[str, str]:
    """Return readiness for dashboard wiring; not an MVP product data endpoint."""

    return {"status": "dashboard-ready"}


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DashboardStats:
    """Return aggregate dashboard metrics for the current user."""

    return metrics_service.calculate_dashboard_stats(db, current_user.id)


@router.get("/equity-curve", response_model=list[EquityCurvePoint])
def get_equity_curve(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30,
) -> list[EquityCurvePoint]:
    """Return the user's equity and balance history for the requested period."""

    return metrics_service.get_equity_curve(db, current_user.id, days)


@router.get("/drawdown-curve", response_model=list[DrawdownCurvePoint])
def get_drawdown_curve(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30,
) -> list[DrawdownCurvePoint]:
    """Return the user's drawdown history for the requested period."""

    return metrics_service.get_drawdown_curve(db, current_user.id, days)
