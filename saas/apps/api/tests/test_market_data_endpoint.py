"""Tests for the market data OHLCV endpoint."""

from unittest.mock import Mock, patch

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


def test_get_ohlcv_returns_standardized_rows() -> None:
    client = TestClient(app)
    frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.5, 102.5],
            "Volume": [1000, 1200],
            "Symbol": ["AAPL", "AAPL"],
        },
        index=pd.to_datetime(["2026-01-02", "2026-01-03"]),
    )

    loader = Mock()
    loader.fetch_data.return_value = frame
    with patch("app.api.v1.endpoints.market_data.DataLoader", return_value=loader):
        response = client.get(
            "/api/v1/market-data/ohlcv",
            params={
                "symbol": "aapl",
                "timeframe": "1d",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["timeframe"] == "1d"
    assert body["row_count"] == 2
    assert body["rows"][0] == {
        "timestamp": "2026-01-02T00:00:00",
        "symbol": "AAPL",
        "open": 100.0,
        "high": 102.0,
        "low": 99.0,
        "close": 101.5,
        "volume": 1000.0,
    }
    loader.fetch_data.assert_called_once_with(
        "AAPL", timeframe="1d", start_date="2026-01-01", end_date="2026-01-31"
    )


def test_get_ohlcv_requires_alpha_vantage_key_for_intraday() -> None:
    client = TestClient(app)

    with patch("app.api.v1.endpoints.market_data.settings.ALPHA_VANTAGE_API_KEY", None):
        response = client.get(
            "/api/v1/market-data/ohlcv",
            params={"symbol": "EURUSD", "timeframe": "5min"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Alpha Vantage API key is required for intraday timeframes."
    )


def test_get_ohlcv_surfaces_provider_errors_as_bad_gateway() -> None:
    client = TestClient(app)
    loader = Mock()
    loader.fetch_data.side_effect = RuntimeError("provider unavailable")

    with patch("app.api.v1.endpoints.market_data.DataLoader", return_value=loader):
        response = client.get(
            "/api/v1/market-data/ohlcv",
            params={"symbol": "AAPL", "timeframe": "1d"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "provider unavailable"


def test_get_ohlcv_rejects_invalid_date_ranges() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/market-data/ohlcv",
        params={
            "symbol": "AAPL",
            "timeframe": "1d",
            "start_date": "2026-02-01",
            "end_date": "2026-01-01",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "start_date must be before or equal to end_date"
