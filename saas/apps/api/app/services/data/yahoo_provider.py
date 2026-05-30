"""Yahoo Finance provider facade.

This wrapper keeps the legacy DataLoader in place while introducing a new
provider-shaped seam for future router wiring.
"""

from __future__ import annotations

from typing import Any


class YahooMarketDataProvider:
    """Fetch daily OHLCV data through the existing DataLoader implementation."""

    def __init__(self, loader: Any | None = None) -> None:
        if loader is None:
            from app.services.data_loader import DataLoader

            loader = DataLoader()
        self.loader = loader

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Any:
        """Fetch standardized OHLCV rows from Yahoo-backed legacy code."""

        return self.loader.fetch_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )


__all__ = ["YahooMarketDataProvider"]
