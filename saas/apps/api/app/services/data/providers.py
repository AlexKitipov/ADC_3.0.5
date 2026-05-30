"""Provider interfaces for the market-data bounded context."""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class MarketDataProvider(Protocol):
    """Protocol implemented by market data providers."""

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Fetch standardized OHLCV data for a symbol."""


__all__ = ["MarketDataProvider"]
