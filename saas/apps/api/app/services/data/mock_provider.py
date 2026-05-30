"""Deterministic in-memory market-data provider for tests and local flows."""

from __future__ import annotations

from typing import Any


class MockMarketDataProvider:
    """Return predictable OHLCV rows without network access."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or [
            {
                "Open": 100.0,
                "High": 101.0,
                "Low": 99.0,
                "Close": 100.5,
                "Volume": 1_000,
            }
        ]

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Any:
        """Fetch deterministic standardized OHLCV rows.

        If pandas is installed, a DataFrame is returned. Otherwise the facade
        falls back to a list of dictionaries so the placeholder remains usable in
        minimal test environments.
        """

        rows = [dict(row, Symbol=symbol, Timeframe=timeframe) for row in self.rows]
        try:
            import pandas as pd
        except ModuleNotFoundError:
            return rows

        index = pd.date_range(start=start_date or "2026-01-01", periods=len(rows), freq="D")
        data = pd.DataFrame(rows, index=index)
        if end_date:
            data = data[data.index <= pd.to_datetime(end_date)]
        return data


__all__ = ["MockMarketDataProvider"]
