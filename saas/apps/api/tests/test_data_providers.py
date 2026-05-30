"""Tests for data provider facades."""

from app.services.data import (
    AlphaVantageMarketDataProvider,
    MockMarketDataProvider,
    YahooMarketDataProvider,
)


class StubLoader:
    def __init__(self) -> None:
        self.calls = []

    def fetch_data(self, **kwargs):
        self.calls.append(kwargs)
        return [{"Open": 1, "High": 2, "Low": 0.5, "Close": 1.5, "Volume": 100}]


def test_mock_provider_returns_standardized_deterministic_rows() -> None:
    data = MockMarketDataProvider().fetch_ohlcv("EURUSD", start_date="2026-01-03")

    first_row = data[0] if isinstance(data, list) else data.iloc[0].to_dict()
    assert first_row["Symbol"] == "EURUSD"
    assert first_row["Timeframe"] == "1d"
    assert first_row["Close"] == 100.5


def test_yahoo_provider_delegates_to_existing_loader() -> None:
    loader = StubLoader()
    provider = YahooMarketDataProvider(loader=loader)

    data = provider.fetch_ohlcv("AAPL", start_date="2026-01-01")

    assert loader.calls == [
        {
            "symbol": "AAPL",
            "timeframe": "1d",
            "start_date": "2026-01-01",
            "end_date": None,
        }
    ]
    assert data[0]["Close"] == 1.5


def test_alpha_vantage_provider_delegates_to_existing_loader() -> None:
    loader = StubLoader()
    provider = AlphaVantageMarketDataProvider(api_key="secret", loader=loader)

    provider.fetch_ohlcv("EURUSD", timeframe="5min", end_date="2026-01-01")

    assert loader.calls[0]["symbol"] == "EURUSD"
    assert loader.calls[0]["timeframe"] == "5min"
    assert loader.calls[0]["end_date"] == "2026-01-01"
