"""Deterministic in-memory market-data provider for tests and local demos."""

from __future__ import annotations

import pandas as pd


class MockMarketDataProvider:
    """Return predictable OHLCV rows without network access."""

    def __init__(self, periods: int = 40) -> None:
        self.periods = periods

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Fetch deterministic standardized OHLCV rows."""

        freq = "D" if timeframe == "1d" else _intraday_frequency(timeframe)
        index = pd.date_range(
            start=pd.to_datetime(start or "2026-01-01"),
            periods=self.periods,
            freq=freq,
        )
        data = pd.DataFrame(
            {
                "Open": [100.0 + value for value in range(self.periods)],
                "High": [101.0 + value for value in range(self.periods)],
                "Low": [99.0 + value for value in range(self.periods)],
                "Close": [100.5 + value for value in range(self.periods)],
                "Volume": [1_000 + value for value in range(self.periods)],
                "Symbol": [symbol] * self.periods,
            },
            index=index,
        )

        if end:
            data = data[data.index <= pd.to_datetime(end)]
        return data

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Backward-compatible alias for earlier provider seam tests."""

        return self.get_ohlcv(symbol, timeframe, start_date, end_date)


def _intraday_frequency(timeframe: str) -> str:
    """Convert API timeframe values such as ``5min`` to pandas frequencies."""

    if timeframe.endswith("min") and timeframe[:-3].isdigit():
        return f"{int(timeframe[:-3])}min"
    return "5min"


__all__ = ["MockMarketDataProvider"]
