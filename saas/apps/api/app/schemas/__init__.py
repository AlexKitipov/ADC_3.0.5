"""Public schema exports grouped by API resource.

Endpoint modules should import schemas from this package-level facade unless they
need a resource module directly.  Keep concrete Pydantic models in the resource
modules so OpenAPI generation and future shared-contract tooling have stable,
well-owned schema boundaries.
"""

from app.schemas.auth import Token, User, UserCreate
from app.schemas.dashboard import DashboardStats, DrawdownCurvePoint, EquityCurvePoint
from app.schemas.lstm import (
    GeneratedCandleRow,
    LSTMGenerateRequest,
    LSTMGenerationResultSchema,
    LSTMJob,
    LSTMJobStatus,
    LSTMTrainRequest,
    LSTMTrainingResultSchema,
)
from app.schemas.indicators import (
    IndicatorCalculationMode,
    IndicatorCalculationRequest,
    IndicatorCalculationResponse,
    IndicatorParameters,
    IndicatorRow,
    IndicatorValues,
)
from app.schemas.orders import BrokerResult, Order, OrderClose, OrderCreate, OrderType
from app.schemas.rl import (
    RLAlgorithm,
    RLEnvironment,
    RLModelArtifact,
    RLTrainingJob,
    RLTrainingRequest,
    RLTrainingResultSchema,
    RLTrainingStatus,
)
from app.schemas.notifications import (
    NotificationAttachmentReference,
    NotificationDeliveryResponse,
    NotificationDeliveryStatus,
    NotificationTestRequest,
    SimulationResultsNotificationRequest,
)
from app.schemas.market_data import (
    MarketDataQuery,
    MarketTickSchema,
    MarketDataResponse,
    MarketDataTimeframe,
    OHLCVRow,
)
from app.schemas.settings import UserSettings, UserSettingsBase, UserSettingsUpdate
from app.schemas.simulations import (
    SimulationArtifact,
    SimulationRequest,
    SimulationResultSchema,
    SimulationRun,
    SimulationStatus,
)
from app.schemas.signals import (
    Signal,
    SignalAction,
    SignalCreate,
    SignalDecisionResponse,
    SignalGenerateRequest,
    SignalGenerateResponse,
)
from app.schemas.strategy import StrategyParameterSpec, StrategyParameterValue
from app.schemas.trades import (
    Trade,
    TradeClose,
    TradeCloseRequest,
    TradeCreate,
    TradeOpenRequest,
)
from app.schemas.trade_journal import (
    JournalArtifactType,
    TradeJournalArtifact,
    TradeJournalEntry,
    TradeJournalExportMetadata,
    TradeJournalImportSummary,
    TradeJournalRelationshipSummary,
    TradeJournalSummary,
)

__all__ = [
    "DashboardStats",
    "DrawdownCurvePoint",
    "EquityCurvePoint",
    "IndicatorCalculationMode",
    "IndicatorCalculationRequest",
    "IndicatorCalculationResponse",
    "IndicatorParameters",
    "IndicatorRow",
    "IndicatorValues",
    "GeneratedCandleRow",
    "LSTMGenerateRequest",
    "LSTMGenerationResultSchema",
    "LSTMJob",
    "LSTMJobStatus",
    "LSTMTrainRequest",
    "LSTMTrainingResultSchema",
    "MarketDataQuery",
    "MarketTickSchema",
    "MarketDataResponse",
    "MarketDataTimeframe",
    "NotificationAttachmentReference",
    "NotificationDeliveryResponse",
    "NotificationDeliveryStatus",
    "NotificationTestRequest",
    "SimulationResultsNotificationRequest",
    "OHLCVRow",
    "BrokerResult",
    "Order",
    "OrderClose",
    "OrderCreate",
    "OrderType",
    "RLAlgorithm",
    "RLEnvironment",
    "RLModelArtifact",
    "RLTrainingJob",
    "RLTrainingRequest",
    "RLTrainingResultSchema",
    "RLTrainingStatus",
    "Signal",
    "SignalAction",
    "SignalCreate",
    "SignalDecisionResponse",
    "SignalGenerateRequest",
    "SignalGenerateResponse",
    "SimulationArtifact",
    "SimulationRequest",
    "SimulationResultSchema",
    "SimulationRun",
    "SimulationStatus",
    "StrategyParameterSpec",
    "StrategyParameterValue",
    "Token",
    "Trade",
    "TradeClose",
    "TradeCloseRequest",
    "TradeCreate",
    "TradeOpenRequest",
    "JournalArtifactType",
    "TradeJournalArtifact",
    "TradeJournalEntry",
    "TradeJournalExportMetadata",
    "TradeJournalImportSummary",
    "TradeJournalRelationshipSummary",
    "TradeJournalSummary",
    "User",
    "UserCreate",
    "UserSettings",
    "UserSettingsBase",
    "UserSettingsUpdate",
]
