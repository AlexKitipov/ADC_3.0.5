"""Public schema exports grouped by API resource.

Endpoint modules should import schemas from this package-level facade unless they
need a resource module directly.  Keep concrete Pydantic models in the resource
modules so OpenAPI generation and future shared-contract tooling have stable,
well-owned schema boundaries.
"""

from app.schemas.auth import Token, User, UserCreate
from app.schemas.dashboard import DashboardStats, DrawdownCurvePoint, EquityCurvePoint
from app.schemas.settings import UserSettings, UserSettingsBase, UserSettingsUpdate
from app.schemas.signals import Signal, SignalAction, SignalCreate
from app.schemas.strategy import StrategyParameterSpec, StrategyParameterValue
from app.schemas.trades import Trade, TradeClose, TradeCreate

__all__ = [
    "DashboardStats",
    "DrawdownCurvePoint",
    "EquityCurvePoint",
    "Signal",
    "SignalAction",
    "SignalCreate",
    "StrategyParameterSpec",
    "StrategyParameterValue",
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
