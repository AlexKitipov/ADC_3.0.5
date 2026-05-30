"""Tests for data provider implementations."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.services.data import (
    AlphaVantageMarketDataProvider,
    MockMarketDataProvider,
    YahooMarketDataProvider,
)


def test_mock_provider_returns_standardized_deterministic_rows() -> None:
    data = MockMarketDataProvider().get_ohlcv("EURUSD", start="2026-01-03")

    first_row = data.iloc[0].to_dict()
    assert first_row["Symbol"] == "EURUSD"
    assert first_row["Close"] == 100.5
    assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume", "Symbol"]


def test_yahoo_provider_standardizes_yfinance_columns() -> None:
    raw = pd.DataFrame(
        {
            "Open": [1.0],
            "High": [2.0],
            "Low": [0.5],
            "Adj Close": [1.5],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2026-01-02"]),
    )

    with patch(
        "app.services.data.yahoo_provider.yf.download", return_value=raw
    ) as download:
        data = YahooMarketDataProvider().get_ohlcv("AAPL", start="2026-01-01")

    download.assert_called_once_with(
        "AAPL", interval="1d", start="2026-01-01", end=None, progress=False
    )
    assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume", "Symbol"]
    assert data.iloc[0]["Close"] == 1.5
    assert data.iloc[0]["Symbol"] == "AAPL"


def test_yahoo_provider_flattens_multi_index_columns() -> None:
    raw = pd.DataFrame(
        [[1.0, 2.0, 0.5, 1.5, 1000]],
        columns=pd.MultiIndex.from_tuples(
            [
                ("Open", "AAPL"),
                ("High", "AAPL"),
                ("Low", "AAPL"),
                ("Close", "AAPL"),
                ("Volume", "AAPL"),
            ]
        ),
    )

    with patch("app.services.data.yahoo_provider.yf.download", return_value=raw):
        data = YahooMarketDataProvider().get_ohlcv("AAPL")

    assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume", "Symbol"]


def test_yahoo_provider_rejects_intraday_timeframes() -> None:
    with pytest.raises(ValueError, match="Alpha Vantage API key required"):
        YahooMarketDataProvider().get_ohlcv("EURUSD", timeframe="5min")


def test_alpha_vantage_provider_converts_payload_and_filters_dates() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "Time Series (5min)": {
            "2026-01-02 09:35:00": {
                "1. open": "1.10000",
                "2. high": "1.20000",
                "3. low": "1.05000",
                "4. close": "1.15000",
                "5. volume": "100",
            },
            "2026-01-02 09:30:00": {
                "1. open": "1.00000",
                "2. high": "1.10000",
                "3. low": "0.95000",
                "4. close": "1.05000",
                "5. volume": "50",
            },
        }
    }

    with patch(
        "app.services.data.alpha_vantage_provider.requests.get", return_value=response
    ) as get:
        data = AlphaVantageMarketDataProvider(api_key="secret").get_ohlcv(
            "EURUSD",
            timeframe="5min",
            start="2026-01-02 09:35:00",
            end="2026-01-02 09:35:00",
        )

    get.assert_called_once()
    assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume", "Symbol"]
    assert list(data.index) == [pd.Timestamp("2026-01-02 09:35:00")]
    assert data.iloc[0]["Open"] == 1.1
    assert data.iloc[0]["Symbol"] == "EURUSD"


def test_alpha_vantage_provider_surfaces_errors() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"Error Message": "Invalid API call"}

    with patch(
        "app.services.data.alpha_vantage_provider.requests.get", return_value=response
    ):
        with pytest.raises(ValueError, match="Invalid API call"):
            AlphaVantageMarketDataProvider(api_key="secret").get_ohlcv(
                "EURUSD", timeframe="5min"
            )
