"""Trading signal API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Signal, User
from app.schemas import Signal as SignalSchema, SignalCreate
from app.security import get_current_user

router = APIRouter()


@router.get("")
def list_signals() -> dict[str, list[dict[str, str]]]:
    """Return the current trading signal collection readiness payload."""

    return {"signals": []}


@router.post("/create", response_model=SignalSchema)
def create_signal(
    signal: SignalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Signal:
    """Create a trading signal owned by the authenticated user."""

    db_signal = Signal(
        user_id=current_user.id,
        symbol=signal.symbol,
        action=signal.action,
        price=signal.price,
        rsi=signal.rsi,
        macd=signal.macd,
    )
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    return db_signal


@router.get("/latest", response_model=list[SignalSchema])
def get_latest_signals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
) -> list[Signal]:
    """Return the authenticated user's most recent trading signals."""

    signals = (
        db.query(Signal)
        .filter(Signal.user_id == current_user.id)
        .order_by(Signal.timestamp.desc())
        .limit(limit)
        .all()
    )
    return signals


@router.get("/by-symbol/{symbol}", response_model=list[SignalSchema])
def get_signals_by_symbol(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
) -> list[Signal]:
    """Return recent authenticated-user signals for a specific symbol."""

    signals = (
        db.query(Signal)
        .filter(Signal.user_id == current_user.id, Signal.symbol == symbol)
        .order_by(Signal.timestamp.desc())
        .limit(limit)
        .all()
    )
    return signals
