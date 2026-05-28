"""Data loading and preprocessing module.

Fetches market data from yfinance and Alpha Vantage APIs.
Handles normalization and feature engineering.
"""

from typing import Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta


class DataLoader:
    """Loads and preprocesses market data from various sources."""

    def __init__(self, alpha_vantage_key: Optional[str] = None):
        """Initialize DataLoader with optional Alpha Vantage API key.
        
        Args:
            alpha_vantage_key: API key for Alpha Vantage intraday data.
        """
        self.alpha_vantage_key = alpha_vantage_key

    def fetch_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch market data for a given symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD', 'AAPL').
            timeframe: Data interval ('1d' for daily, or intraday like '5min', '15min').
            start_date: Start date as string (YYYY-MM-DD).
            end_date: End date as string (YYYY-MM-DD).
            
        Returns:
            DataFrame with OHLCV data (Open, High, Low, Close, Volume).
            
        Raises:
            ValueError: If intraday data requested without Alpha Vantage key.
        """
        if timeframe == "1d":
            return self._fetch_daily(symbol, start_date, end_date)
        else:
            if not self.alpha_vantage_key:
                raise ValueError(
                    "Alpha Vantage API key required for intraday timeframes."
                )
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
                symbol, interval="1d", start=start_date, end=end_date, progress=False
            )
            
            # Handle multi-index columns (when multiple symbols)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]
            
            # Standardize column names
            data.columns = pd.Index([str(col).strip().upper() for col in data.columns])
            data.columns.name = None
            
            # Handle Adjusted Close
            if "ADJ CLOSE" in data.columns and "CLOSE" not in data.columns:
                data = data.rename(columns={"ADJ CLOSE": "CLOSE"})
            
            # Select only OHLCV
            required_cols = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]
            available = [col for col in required_cols if col in data.columns]
            data = data[available]
            
            # Standardize capitalization
            data.columns = [col.capitalize() for col in data.columns]
            data["Symbol"] = symbol
            
            return data
        except Exception as e:
            raise RuntimeError(f"Error fetching daily data for {symbol}: {e}")

    def _fetch_intraday(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch intraday OHLCV data using Alpha Vantage."""
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": timeframe,
            "apikey": self.alpha_vantage_key,
            "outputsize": "full",
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            json_data = response.json()
            
            key = f"Time Series ({timeframe})"
            if key not in json_data:
                error_msg = json_data.get("Note", json_data.get("Error Message", "Unknown error"))
                raise ValueError(f"Alpha Vantage error: {error_msg}")
            
            df = pd.DataFrame.from_dict(json_data[key], orient="index")
            df = df.rename(
                columns={
                    "1. open": "Open",
                    "2. high": "High",
                    "3. low": "Low",
                    "4. close": "Close",
                    "5. volume": "Volume",
                }
            )
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df.astype(float)
            
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df.index <= pd.to_datetime(end_date)]
            
            df["Symbol"] = symbol
            return df
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error fetching intraday data from Alpha Vantage: {e}")

    @staticmethod
    def normalize_price(value: float, digits: int = 5) -> float:
        """Normalize price to specified decimal places (MQL4-like behavior).
        
        Args:
            value: Price value to normalize.
            digits: Number of decimal places.
            
        Returns:
            Normalized price value.
        """
        return round(value, digits)

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> bool:
        """Validate that DataFrame contains required OHLCV columns.
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            True if all OHLCV columns present, False otherwise.
        """
        required = {"Open", "High", "Low", "Close", "Volume"}
        return required.issubset(set(df.columns))
