"""User-scoped trade history service functions.

The trade service owns the persisted SaaS trade-history lifecycle. It records
open/closed trades and PnL for the authenticated user's history without sending
broker orders; executable broker activity remains in the orders service.
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Trade, User
from app.schemas.trades import TradeCloseRequest, TradeOpenRequest


def list_open_trades(db: Session, user: User) -> list[Trade]:
    """Return open persisted trades owned by ``user``."""

    return (
        db.query(Trade)
        .filter(Trade.user_id == user.id, Trade.status == "open")
        .order_by(Trade.entry_time.desc(), Trade.id.desc())
        .all()
    )


def list_closed_trades(db: Session, user: User, limit: int = 50) -> list[Trade]:
    """Return recently closed persisted trades owned by ``user``."""

    return (
        db.query(Trade)
        .filter(Trade.user_id == user.id, Trade.status == "closed")
        .order_by(Trade.exit_time.desc(), Trade.id.desc())
        .limit(limit)
        .all()
    )


def open_trade(db: Session, user: User, request: TradeOpenRequest) -> Trade:
    """Persist a user-visible open trade-history row.

    This function intentionally does not call a broker adapter or MockBrokerAPI;
    broker execution is handled exclusively by the orders domain.
    """

    trade = Trade(
        user_id=user.id,
        symbol=request.symbol.upper(),
        entry_price=request.entry_price,
        status="open",
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def close_trade(
    db: Session,
    user: User,
    trade_id: int,
    request: TradeCloseRequest,
) -> Trade:
    """Close one of ``user``'s open persisted trades and store PnL fields."""

    trade = (
        db.query(Trade)
        .filter(Trade.id == trade_id, Trade.user_id == user.id)
        .first()
    )
    if trade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found",
        )
    if trade.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trade is already closed",
        )

    pnl = request.exit_price - trade.entry_price
    trade.exit_price = request.exit_price
    trade.exit_time = datetime.utcnow()
    trade.status = "closed"
    trade.pnl = pnl
    trade.pnl_percent = (pnl / trade.entry_price) * 100

    db.commit()
    db.refresh(trade)
    return trade
