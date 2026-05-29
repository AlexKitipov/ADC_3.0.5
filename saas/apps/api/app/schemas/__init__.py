"""Pydantic request and response schemas for the ADC Trading Platform API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for registering a user account."""

    email: EmailStr
    username: str
    password: str


class User(BaseModel):
    """Public user response."""

    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str


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


class TradeCreate(BaseModel):
    """Payload for opening a simple persisted trade record."""

    symbol: str = Field(min_length=1, max_length=32)
    entry_price: float = Field(gt=0)


class TradeClose(BaseModel):
    """Payload for closing a simple persisted trade record."""

    exit_price: float = Field(gt=0)


class Trade(BaseModel):
    """Trade response."""

    id: int
    symbol: str
    entry_price: float
    exit_price: float | None
    entry_time: datetime
    exit_time: datetime | None
    pnl: float | None
    pnl_percent: float | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    """Dashboard performance metrics."""

    total_balance: float
    current_equity: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    monthly_pnl: float


class EquityCurvePoint(BaseModel):
    """Single timestamped balance and equity point for dashboard charts."""

    timestamp: datetime
    equity: float
    balance: float


class DrawdownCurvePoint(BaseModel):
    """Single timestamped drawdown point for dashboard charts."""

    timestamp: datetime
    drawdown: float


class UserSettingsBase(BaseModel):
    """Shared trading and notification settings fields.

    Percent-like values are stored as decimal fractions: ``0.02`` means 2% risk
    per trade and ``0.005`` means a 0.5% grid step.
    """

    symbols: list[str]
    timeframe: str
    balance: float
    risk_per_trade: float = Field(
        description="Decimal fraction risk per trade; 0.02 means 2%."
    )
    grid_levels: int
    grid_step_pct: float = Field(
        description="Decimal fraction grid step; 0.005 means 0.5%."
    )
    martingale_factor: float
    enable_trading: bool
    email_notifications: bool


class UserSettings(UserSettingsBase):
    """Trading and notification settings response."""

    id: int

    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdate(UserSettingsBase):
    """Complete payload for replacing user trading and notification preferences."""

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "DashboardStats",
    "DrawdownCurvePoint",
    "EquityCurvePoint",
    "Signal",
    "SignalAction",
    "SignalCreate",
    "Token",
    "Trade",
    "TradeClose",
    "TradeCreate",
    "User",
    "UserCreate",
    "UserSettings",
    "UserSettingsBase",
    "UserSettingsUpdate",
]
