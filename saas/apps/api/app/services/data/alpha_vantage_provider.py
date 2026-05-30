"""Alpha Vantage market-data provider."""

from __future__ import annotations

import pandas as pd
import requests


class AlphaVantageMarketDataProvider:
    """Fetch intraday OHLCV data from Alpha Vantage."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Alpha Vantage API key required for intraday timeframes.")
        self.api_key = api_key

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5min",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Fetch standardized intraday OHLCV rows from Alpha Vantage."""

        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": timeframe,
            "apikey": self.api_key,
            "outputsize": "full",
        }

        try:
            response = requests.get(
                "https://www.alphavantage.co/query", params=params, timeout=30
            )
            response.raise_for_status()
            json_data = response.json()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"Error fetching intraday data from Alpha Vantage: {exc}"
            ) from exc

        key = f"Time Series ({timeframe})"
        if key not in json_data:
            error_message = json_data.get(
                "Note", json_data.get("Error Message", "Unknown error")
            )
            raise ValueError(f"Alpha Vantage error: {error_message}")

        data = pd.DataFrame.from_dict(json_data[key], orient="index")
        data = data.rename(
            columns={
                "1. open": "Open",
                "2. high": "High",
                "3. low": "Low",
                "4. close": "Close",
                "5. volume": "Volume",
            }
        )
        data.index = pd.to_datetime(data.index)
        data = data.sort_index()
        data = data.astype(float)

        if start:
            data = data[data.index >= pd.to_datetime(start)]
        if end:
            data = data[data.index <= pd.to_datetime(end)]

        data["Symbol"] = symbol
        return data

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5min",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Backward-compatible alias for earlier provider seam tests."""

        return self.get_ohlcv(symbol, timeframe, start_date, end_date)


__all__ = ["AlphaVantageMarketDataProvider"]
