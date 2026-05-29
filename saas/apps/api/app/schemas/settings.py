"""User trading preference and notification setting schemas."""

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = ["UserSettings", "UserSettingsBase", "UserSettingsUpdate"]
