"""Tests for market data loading and normalization helpers."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.services.data_loader import DataLoader


def test_fetch_daily_standardizes_yfinance_columns() -> None:
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

    with patch("app.services.data_loader.yf.download", return_value=raw) as download:
        data = DataLoader().fetch_data("AAPL", start_date="2026-01-01")

    download.assert_called_once_with(
        "AAPL", interval="1d", start="2026-01-01", end=None, progress=False
    )
    assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume", "Symbol"]
    assert data.iloc[0]["Close"] == 1.5
    assert data.iloc[0]["Symbol"] == "AAPL"


def test_fetch_daily_flattens_multi_index_columns() -> None:
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

    with patch("app.services.data_loader.yf.download", return_value=raw):
        data = DataLoader().fetch_data("AAPL")

    assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume", "Symbol"]


def test_fetch_intraday_requires_alpha_vantage_key() -> None:
    with pytest.raises(ValueError, match="Alpha Vantage API key required"):
        DataLoader().fetch_data("EURUSD", timeframe="5min")


def test_fetch_intraday_converts_alpha_vantage_payload_and_filters_dates() -> None:
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

    with patch("app.services.data_loader.requests.get", return_value=response) as get:
        data = DataLoader(alpha_vantage_key="secret").fetch_data(
            "EURUSD",
            timeframe="5min",
            start_date="2026-01-02 09:35:00",
            end_date="2026-01-02 09:35:00",
        )

    get.assert_called_once()
    assert list(data.columns) == ["Open", "High", "Low", "Close", "Volume", "Symbol"]
    assert list(data.index) == [pd.Timestamp("2026-01-02 09:35:00")]
    assert data.iloc[0]["Open"] == 1.1
    assert data.iloc[0]["Symbol"] == "EURUSD"


def test_fetch_intraday_surfaces_alpha_vantage_errors() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"Error Message": "Invalid API call"}

    with patch("app.services.data_loader.requests.get", return_value=response):
        with pytest.raises(ValueError, match="Invalid API call"):
            DataLoader(alpha_vantage_key="secret").fetch_data("EURUSD", timeframe="5min")


def test_normalize_price_and_validate_ohlcv() -> None:
    data = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "Symbol"])

    assert DataLoader.normalize_price(1.234567, digits=4) == 1.2346
    assert DataLoader.validate_ohlcv(data) is True
    assert DataLoader.validate_ohlcv(data.drop(columns=["Volume"])) is False
