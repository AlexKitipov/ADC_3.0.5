"""Trading-session lifecycle request and response schemas."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TradingSessionConfigSchema(BaseModel):
    """Public configuration for creating a mock live trading session."""

    symbol: str = Field(default="EURUSD", min_length=1, max_length=32)
    initial_price: float = Field(default=1.20000, gt=0)
    price_volatility: float = Field(default=0.0001, ge=0)
    stream_interval: float = Field(default=1.0, ge=0.01, le=60)
    order_volume: float = Field(default=0.1, gt=0)
    slippage: int = Field(default=5, ge=0, le=1000)
    magic: int = Field(default=305, ge=0)
    broker_error_rate: float = Field(default=0.1, ge=0, le=1)
    broker_trade_allowed: bool = False
    retry_attempts: int = Field(default=3, ge=1, le=10)
    sleep_time: float = Field(default=0.1, ge=0, le=5)
    sleep_maximum: float = Field(default=0.5, ge=0, le=10)
    max_close_duration: float = Field(default=5.0, gt=0, le=120)
    random_seed: int | None = None


class TradingSessionCreate(BaseModel):
    """Payload for creating a user-scoped session.

    Sessions and events are currently stored in process memory because the
    backing ``TradingSession`` owns live broker and market-stream objects that
    cannot be restored safely from database rows. Persisted audit trails can be
    added behind the same response schemas later.
    """

    config: TradingSessionConfigSchema = Field(default_factory=TradingSessionConfigSchema)
    auto_start: bool = False


class SessionEventRead(BaseModel):
    """Single event emitted by a trading session."""

    type: str
    message: str
    timestamp: str
    details: dict[str, Any] = Field(default_factory=dict)


class TradingSessionState(BaseModel):
    """Serializable state for a live trading session."""

    id: str
    status: Literal["created", "running", "stopped"]
    is_trading_active: bool
    broker_trade_allowed: bool
    symbol: str
    config: TradingSessionConfigSchema
    last_tick: dict[str, Any] | None = None
    last_action: Any = None
    open_positions: int
    event_count: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "SessionEventRead",
    "TradingSessionConfigSchema",
    "TradingSessionCreate",
    "TradingSessionState",
]
