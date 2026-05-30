"""Provider interfaces for the market-data bounded context."""

from __future__ import annotations

from typing import Any, Protocol


class MarketDataProvider(Protocol):
    """Protocol implemented by market data providers."""

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Any:
        """Fetch standardized OHLCV data for a symbol."""


__all__ = ["MarketDataProvider"]
