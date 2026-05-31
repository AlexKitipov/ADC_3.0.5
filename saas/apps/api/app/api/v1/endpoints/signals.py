"""Trading signal API endpoints."""

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Signal, User, UserSettings, default_user_settings_values
from app.schemas import (
    Signal as SignalSchema,
    SignalCreate,
    SignalGenerateRequest,
    SignalGenerateResponse,
)
from app.security import get_current_user
from app.services.data_loader import get_market_data_provider
from app.services.signal_engine import decision_to_signal_values, generate_signal

router = APIRouter()


@router.get(
    "",
    tags=["Readiness / Demo"],
    summary="Readiness-only signal collection placeholder",
)
def list_signals() -> dict[str, list[dict[str, str]]]:
    """Return a readiness/demo placeholder; not an MVP product data endpoint."""

    return {"signals": []}


@router.post("/generate", response_model=SignalGenerateResponse)
def generate_signal_for_current_user(
    request: SignalGenerateRequest = Body(default_factory=SignalGenerateRequest),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Generate, persist, and return a signal for the authenticated user."""

    user_settings = _get_or_create_user_settings(current_user.id, db)
    symbol = _resolve_symbol(request.symbol, user_settings)
    timeframe = request.timeframe or user_settings.timeframe
    strategy_settings = dict(request.strategy_settings)

    decision = generate_signal(
        symbol=symbol,
        timeframe=timeframe,
        strategy_settings=strategy_settings,
        data_provider=get_market_data_provider(),
    )
    signal_values = decision_to_signal_values(decision)
    db_signal = Signal(user_id=current_user.id, **signal_values)

    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)

    return {"signal": db_signal, "decision": decision.model_dump()}


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


def _get_or_create_user_settings(user_id: int, db: Session) -> UserSettings:
    """Return settings for signal generation, creating defaults if needed."""

    user_settings = (
        db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    )
    if user_settings is None:
        user_settings = UserSettings(user_id=user_id, **default_user_settings_values())
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    return user_settings


def _resolve_symbol(request_symbol: str | None, user_settings: UserSettings) -> str:
    """Resolve request symbol override or first configured settings symbol."""

    if request_symbol:
        return request_symbol.upper()

    symbols = user_settings.symbols or default_user_settings_values()["symbols"]
    if not symbols:
        symbols = default_user_settings_values()["symbols"]
    return str(symbols[0]).upper()
