"""User trading preference and notification setting schemas."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_SYMBOLS = ["EURUSD", "GBPUSD"]
DEFAULT_TIMEFRAME = "1d"
DEFAULT_BALANCE = 10_000.0
DEFAULT_RISK_PER_TRADE = 0.02
DEFAULT_GRID_LEVELS = 3
DEFAULT_GRID_STEP_PCT = 0.005
DEFAULT_MARTINGALE_FACTOR = 1.1
DEFAULT_ENABLE_TRADING = False
DEFAULT_EMAIL_NOTIFICATIONS = True

SUPPORTED_TIMEFRAMES = ("5m", "15m", "1h", "4h", "1d")

Symbols = Annotated[
    list[str],
    Field(
        min_length=1,
        max_length=20,
        examples=[DEFAULT_SYMBOLS],
        description="One or more trading symbols configured for MVP data requests.",
    ),
]
Timeframe = Literal["5m", "15m", "1h", "4h", "1d"]
Balance = Annotated[
    float,
    Field(ge=0, le=1_000_000_000, examples=[DEFAULT_BALANCE]),
]
RiskPerTrade = Annotated[
    float,
    Field(
        ge=0.001,
        le=0.2,
        examples=[DEFAULT_RISK_PER_TRADE],
        description="Decimal fraction risk per trade; 0.02 means 2%.",
    ),
]
GridLevels = Annotated[int, Field(ge=1, le=100, examples=[DEFAULT_GRID_LEVELS])]
GridStepPct = Annotated[
    float,
    Field(
        ge=0.0001,
        le=0.2,
        examples=[DEFAULT_GRID_STEP_PCT],
        description="Decimal fraction grid step; 0.005 means 0.5%.",
    ),
]
MartingaleFactor = Annotated[
    float,
    Field(ge=1.0, le=10.0, examples=[DEFAULT_MARTINGALE_FACTOR]),
]


def normalize_symbols(symbols: list[str]) -> list[str]:
    """Trim, uppercase, deduplicate, and reject blank symbol values."""

    normalized: list[str] = []
    for symbol in symbols:
        cleaned_symbol = symbol.strip().upper()
        if not cleaned_symbol:
            raise ValueError("symbols must not contain blank values")
        if cleaned_symbol not in normalized:
            normalized.append(cleaned_symbol)
    return normalized


class UserSettingsBase(BaseModel):
    """Shared trading and notification settings fields.

    Percent-like values are stored as decimal fractions: ``0.02`` means 2% risk
    per trade and ``0.005`` means a 0.5% grid step.
    """

    symbols: Symbols = Field(default_factory=lambda: list(DEFAULT_SYMBOLS))
    timeframe: Timeframe = DEFAULT_TIMEFRAME
    balance: Balance = DEFAULT_BALANCE
    risk_per_trade: RiskPerTrade = DEFAULT_RISK_PER_TRADE
    grid_levels: GridLevels = DEFAULT_GRID_LEVELS
    grid_step_pct: GridStepPct = DEFAULT_GRID_STEP_PCT
    martingale_factor: MartingaleFactor = DEFAULT_MARTINGALE_FACTOR
    enable_trading: bool = DEFAULT_ENABLE_TRADING
    email_notifications: bool = DEFAULT_EMAIL_NOTIFICATIONS

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, symbols: list[str]) -> list[str]:
        """Normalize and validate configured trading symbols."""

        return normalize_symbols(symbols)


class UserSettings(UserSettingsBase):
    """Trading and notification settings response."""

    id: int

    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdate(BaseModel):
    """Complete payload for replacing user trading and notification preferences."""

    symbols: Symbols
    timeframe: Timeframe
    balance: Balance
    risk_per_trade: RiskPerTrade
    grid_levels: GridLevels
    grid_step_pct: GridStepPct
    martingale_factor: MartingaleFactor
    enable_trading: bool
    email_notifications: bool

    model_config = ConfigDict(extra="forbid")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, symbols: list[str]) -> list[str]:
        """Normalize and validate configured trading symbols."""

        return normalize_symbols(symbols)


__all__ = [
    "DEFAULT_BALANCE",
    "DEFAULT_EMAIL_NOTIFICATIONS",
    "DEFAULT_ENABLE_TRADING",
    "DEFAULT_GRID_LEVELS",
    "DEFAULT_GRID_STEP_PCT",
    "DEFAULT_MARTINGALE_FACTOR",
    "DEFAULT_RISK_PER_TRADE",
    "DEFAULT_SYMBOLS",
    "DEFAULT_TIMEFRAME",
    "SUPPORTED_TIMEFRAMES",
    "UserSettings",
    "UserSettingsBase",
    "UserSettingsUpdate",
]
