"""Data loading and preprocessing helpers for market OHLCV data.

The :class:`DataLoader` centralizes access to yfinance daily data and Alpha
Vantage intraday data while returning consistently shaped pandas DataFrames.
"""

from typing import Optional

import pandas as pd
import requests
import yfinance as yf


class DataLoader:
    """Load and preprocess market data from supported providers."""

    def __init__(self, alpha_vantage_key: Optional[str] = None) -> None:
        """Initialize the loader with an optional Alpha Vantage API key.

        Args:
            alpha_vantage_key: API key used for Alpha Vantage intraday data.
        """

        self.alpha_vantage_key = alpha_vantage_key

    def fetch_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch market data for a symbol and interval.

        Args:
            symbol: Trading symbol, for example ``EURUSD`` or ``AAPL``.
            timeframe: Data interval. Use ``1d`` for yfinance daily data or an
                Alpha Vantage intraday interval such as ``5min`` or ``15min``.
            start_date: Optional inclusive start date in ``YYYY-MM-DD`` format.
            end_date: Optional inclusive end date in ``YYYY-MM-DD`` format.

        Returns:
            A DataFrame containing standardized ``Open``, ``High``, ``Low``,
            ``Close``, ``Volume``, and ``Symbol`` columns when available.

        Raises:
            ValueError: If intraday data is requested without an Alpha Vantage
                API key or if Alpha Vantage returns an error payload.
            RuntimeError: If an upstream request fails.
        """

        if timeframe == "1d":
            return self._fetch_daily(symbol, start_date, end_date)

        if not self.alpha_vantage_key:
            raise ValueError("Alpha Vantage API key required for intraday timeframes.")

        return self._fetch_intraday(symbol, timeframe, start_date, end_date)

    def _fetch_daily(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV data using yfinance."""

        try:
            data = yf.download(
                symbol,
                interval="1d",
                start=start_date,
                end=end_date,
                progress=False,
            )
        except Exception as exc:
            raise RuntimeError(f"Error fetching daily data for {symbol}: {exc}") from exc

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [column[0] for column in data.columns]

        data.columns = pd.Index([str(column).strip().upper() for column in data.columns])
        data.columns.name = None

        if "ADJ CLOSE" in data.columns and "CLOSE" not in data.columns:
            data = data.rename(columns={"ADJ CLOSE": "CLOSE"})

        required_columns = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]
        available_columns = [
            column for column in required_columns if column in data.columns
        ]
        data = data.loc[:, available_columns]
        data.columns = [column.capitalize() for column in data.columns]
        data["Symbol"] = symbol

        return data

    def _fetch_intraday(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch intraday OHLCV data using Alpha Vantage."""

        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": timeframe,
            "apikey": self.alpha_vantage_key,
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

        if start_date:
            data = data[data.index >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data.index <= pd.to_datetime(end_date)]

        data["Symbol"] = symbol
        return data

    @staticmethod
    def normalize_price(value: float, digits: int = 5) -> float:
        """Normalize a price to the requested number of decimal places."""

        return round(value, digits)

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> bool:
        """Return whether a DataFrame contains required OHLCV columns."""

        required = {"Open", "High", "Low", "Close", "Volume"}
        return required.issubset(set(df.columns))
