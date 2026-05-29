"""Trading signal request and response schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class SignalAction(str, Enum):
    """Allowed trading signal action values."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalCreate(BaseModel):
    """Payload for creating a trading signal."""

    symbol: str
    action: SignalAction
    price: float
    rsi: float
    macd: float


class Signal(BaseModel):
    """Trading signal response."""

    id: int
    symbol: str
    action: SignalAction
    price: float
    rsi: float
    macd: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = ["Signal", "SignalAction", "SignalCreate"]
