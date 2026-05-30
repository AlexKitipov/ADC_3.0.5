"""Alpha Vantage provider facade."""

from __future__ import annotations

from typing import Any


class AlphaVantageMarketDataProvider:
    """Fetch intraday OHLCV data through the existing DataLoader implementation."""

    def __init__(self, api_key: str, loader: Any | None = None) -> None:
        if loader is None:
            from app.services.data_loader import DataLoader

            loader = DataLoader(alpha_vantage_key=api_key)
        self.loader = loader

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5min",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Any:
        """Fetch standardized OHLCV rows from Alpha Vantage-backed legacy code."""

        return self.loader.fetch_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )


__all__ = ["AlphaVantageMarketDataProvider"]
