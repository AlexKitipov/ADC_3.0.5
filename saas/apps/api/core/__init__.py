"""ADC Trading Core Modules.

This package contains the core trading logic extracted from the notebook:
- data_loader: Market data fetching and preprocessing
- indicators: Technical analysis indicators (RSI, MACD, Bollinger Bands, ATR, Pivots)
- lstm_model: LSTM model for price generation
- rl_env: Reinforcement learning environment (PivotEnv)
- broker_sim: Mock broker API and order management
"""

__version__ = "1.0.0"

from .indicators import TechnicalIndicators

__all__ = ["TechnicalIndicators", "LSTMPriceGenerator"]


def __getattr__(name: str):
    """Lazily load optional heavy core modules."""
    if name == "LSTMPriceGenerator":
        from .lstm_model import LSTMPriceGenerator

        return LSTMPriceGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
