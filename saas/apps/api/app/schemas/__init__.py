"""Pydantic request and response schemas for the ADC Trading Platform API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


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


class SignalCreate(BaseModel):
    """Payload for creating a trading signal."""

    symbol: str
    action: str
    price: float
    rsi: float
    macd: float


class Signal(BaseModel):
    """Trading signal response."""

    id: int
    symbol: str
    action: str
    price: float
    rsi: float
    macd: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class TradeCreate(BaseModel):
    """Payload for opening a trade."""

    symbol: str
    entry_price: float


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


class UserSettingsUpdate(BaseModel):
    """Payload for replacing user trading and notification preferences."""

    symbols: list[str]
    timeframe: str
    balance: float
    risk_per_trade: float
    grid_levels: int
    grid_step_pct: float
    martingale_factor: float
    enable_trading: bool
    email_notifications: bool


__all__ = [
    "DashboardStats",
    "Signal",
    "SignalCreate",
    "Token",
    "Trade",
    "TradeCreate",
    "User",
    "UserCreate",
    "UserSettingsUpdate",
]
