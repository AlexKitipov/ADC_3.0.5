"""Trade API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trade, User
from app.schemas import Trade as TradeSchema, TradeClose, TradeCreate
from app.security import get_current_user

router = APIRouter()


@router.get("")
def list_trades() -> dict[str, list[dict[str, str]]]:
    """Return the current trade collection readiness payload."""

    return {"trades": []}


@router.post("/open", response_model=TradeSchema)
def open_trade(
    trade: TradeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Trade:
    """Persist a simple open trade record for the authenticated user.

    This endpoint records a user-visible trade journal entry. It does not submit
    an executable broker order or invoke the richer order-management service.
    """

    db_trade = Trade(
        user_id=current_user.id,
        symbol=trade.symbol.upper(),
        entry_price=trade.entry_price,
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade


@router.post("/close/{trade_id}", response_model=TradeSchema)
def close_trade(
    trade_id: int,
    trade_close: TradeClose,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Trade:
    """Close an authenticated user's simple trade record and calculate PnL."""

    trade = (
        db.query(Trade)
        .filter(Trade.id == trade_id, Trade.user_id == current_user.id)
        .first()
    )

    if trade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found"
        )
    if trade.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Trade is already closed"
        )

    trade.exit_price = trade_close.exit_price
    trade.exit_time = datetime.utcnow()
    trade.status = "closed"
    trade.pnl = trade_close.exit_price - trade.entry_price
    trade.pnl_percent = (trade.pnl / trade.entry_price) * 100

    db.commit()
    db.refresh(trade)
    return trade


@router.get("/open", response_model=list[TradeSchema])
def get_open_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Trade]:
    """Return all currently open trades for the authenticated user."""

    trades = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id, Trade.status == "open")
        .all()
    )
    return trades


@router.get("/closed", response_model=list[TradeSchema])
def get_closed_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
) -> list[Trade]:
    """Return recently closed trades for the authenticated user."""

    trades = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id, Trade.status == "closed")
        .order_by(Trade.exit_time.desc())
        .limit(limit)
        .all()
    )
    return trades
