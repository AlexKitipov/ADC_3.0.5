"""Trade API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trade, User
from app.schemas import Trade as TradeSchema
from app.schemas import TradeCloseRequest, TradeOpenRequest
from app.security import get_current_user
from app.services.trade_service import (
    close_trade as close_user_trade,
    list_closed_trades,
    list_open_trades,
    open_trade as open_user_trade,
)

router = APIRouter()


@router.get(
    "",
    tags=["Readiness / Demo"],
    summary="Readiness-only trade collection placeholder",
)
def list_trades() -> dict[str, list[dict[str, str]]]:
    """Return a readiness/demo placeholder; not an MVP product data endpoint."""

    return {"trades": []}


@router.get("/open", response_model=list[TradeSchema])
def get_open_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Trade]:
    """Return all currently open trades for the authenticated user."""

    return list_open_trades(db=db, user=current_user)


@router.get("/closed", response_model=list[TradeSchema])
def get_closed_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=250),
) -> list[Trade]:
    """Return recently closed trades for the authenticated user."""

    return list_closed_trades(db=db, user=current_user, limit=limit)


@router.post("/open", response_model=TradeSchema)
def open_trade(
    trade: TradeOpenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Trade:
    """Persist a user-visible trade-history row without broker execution."""

    return open_user_trade(db=db, user=current_user, request=trade)


@router.post("/close/{trade_id}", response_model=TradeSchema)
def close_trade(
    trade_id: int,
    trade_close: TradeCloseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Trade:
    """Close an authenticated user's persisted trade-history row."""

    return close_user_trade(
        db=db,
        user=current_user,
        trade_id=trade_id,
        request=trade_close,
    )
