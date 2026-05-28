"""SQLAlchemy persistence models for the ADC Trading Platform API."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


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
    signals = relationship("Signal", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    """Per-user trading and notification preferences."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbols = Column(JSON, default=lambda: ["EURUSD", "GBPUSD"], nullable=False)
    timeframe = Column(String, default="1d", nullable=False)
    balance = Column(Float, default=10000.0, nullable=False)
    risk_per_trade = Column(Float, default=0.02, nullable=False)
    grid_levels = Column(Integer, default=3, nullable=False)
    grid_step_pct = Column(Float, default=0.005, nullable=False)
    martingale_factor = Column(Float, default=1.1, nullable=False)
    enable_trading = Column(Boolean, default=False, nullable=False)
    email_notifications = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="settings")


class Signal(Base):
    """Generated market signal for a user."""

    __tablename__ = "signals"

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
    "Signal",
    "Trade",
    "User",
    "UserSettings",
]
