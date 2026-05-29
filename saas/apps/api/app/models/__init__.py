"""SQLAlchemy persistence models for the ADC Trading Platform API."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.db.session import Base

SIGNAL_ACTION_VALUES = ("BUY", "SELL", "HOLD")

DEFAULT_USER_SETTINGS = {
    "symbols": ["EURUSD", "GBPUSD"],
    "timeframe": "1d",
    "balance": 10000.0,
    "risk_per_trade": 0.02,
    "grid_levels": 3,
    "grid_step_pct": 0.005,
    "martingale_factor": 1.1,
    "enable_trading": False,
    "email_notifications": True,
}


def default_user_settings_values() -> dict[str, object]:
    """Return a copy of the persisted default user settings values.

    Percent-like values use decimal fraction semantics: ``0.02`` means 2% and
    ``0.005`` means 0.5%.
    """

    return {**DEFAULT_USER_SETTINGS, "symbols": list(DEFAULT_USER_SETTINGS["symbols"])}


class User(Base):
    """Application user account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    settings = relationship(
        "UserSettings", back_populates="user", cascade="all, delete-orphan"
    )
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    signals = relationship(
        "Signal", back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(Base):
    """Per-user trading and notification preferences."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbols = Column(
        JSON,
        default=lambda: list(DEFAULT_USER_SETTINGS["symbols"]),
        nullable=False,
    )
    timeframe = Column(
        String, default=DEFAULT_USER_SETTINGS["timeframe"], nullable=False
    )
    balance = Column(Float, default=DEFAULT_USER_SETTINGS["balance"], nullable=False)
    risk_per_trade = Column(
        Float, default=DEFAULT_USER_SETTINGS["risk_per_trade"], nullable=False
    )
    grid_levels = Column(
        Integer, default=DEFAULT_USER_SETTINGS["grid_levels"], nullable=False
    )
    grid_step_pct = Column(
        Float, default=DEFAULT_USER_SETTINGS["grid_step_pct"], nullable=False
    )
    martingale_factor = Column(
        Float, default=DEFAULT_USER_SETTINGS["martingale_factor"], nullable=False
    )
    enable_trading = Column(
        Boolean, default=DEFAULT_USER_SETTINGS["enable_trading"], nullable=False
    )
    email_notifications = Column(
        Boolean, default=DEFAULT_USER_SETTINGS["email_notifications"], nullable=False
    )

    user = relationship("User", back_populates="settings")


class Signal(Base):
    """Generated market signal for a user."""

    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint(
            "action IN ('BUY', 'SELL', 'HOLD')",
            name="ck_signals_action_allowed",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    rsi = Column(Float, nullable=False)
    macd = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="signals")


class Trade(Base):
    """Trade opened by the platform for a user."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    entry_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    status = Column(String, default="open", nullable=False)

    user = relationship("User", back_populates="trades")


class EquitySnapshot(Base):
    """Point-in-time account equity metrics."""

    __tablename__ = "equity_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    balance = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    drawdown = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


__all__ = [
    "EquitySnapshot",
    "SIGNAL_ACTION_VALUES",
    "Signal",
    "Trade",
    "User",
    "UserSettings",
    "default_user_settings_values",
]
