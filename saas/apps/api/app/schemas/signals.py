"""Trading signal request and response schemas."""

from datetime import datetime
from enum import Enum

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SignalAction(str, Enum):
    """Allowed trading signal action values."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalGenerateRequest(BaseModel):
    """Payload for deterministic signal generation.

    ``symbol`` and ``timeframe`` are optional so a future endpoint can apply
    API-level defaults without coupling those defaults to persistence schemas.
    ``strategy_settings`` allows callers/tests to override indicator periods and
    RSI thresholds while remaining a response-only, non-DB DTO in this PR.
    """

    symbol: str | None = None
    timeframe: str | None = None
    strategy_settings: dict[str, Any] = Field(default_factory=dict)


class SignalDecisionResponse(BaseModel):
    """Response DTO for deterministic signal generation results."""

    symbol: str
    action: SignalAction
    confidence: float
    explanation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


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


__all__ = [
    "Signal",
    "SignalAction",
    "SignalCreate",
    "SignalDecisionResponse",
    "SignalGenerateRequest",
]
