"""Tests for MARKET_DATA_PROVIDER provider selection."""

from __future__ import annotations

import pytest

from app.services.data import (
    AlphaVantageMarketDataProvider,
    MockMarketDataProvider,
    YahooMarketDataProvider,
)
from app.services.data_loader import DataLoader, get_market_data_provider


def test_factory_defaults_to_yahoo_when_provider_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MARKET_DATA_PROVIDER", raising=False)

    provider = get_market_data_provider()

    assert isinstance(provider, YahooMarketDataProvider)


def test_factory_selects_mock_provider_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "mock")

    provider = get_market_data_provider()
    data = provider.get_ohlcv("AAPL", start="2026-01-01", end="2026-01-03")

    assert isinstance(provider, MockMarketDataProvider)
    assert len(data) == 3
    assert data.iloc[0]["Symbol"] == "AAPL"
    assert data.iloc[0]["Close"] == 100.5


def test_factory_selects_alpha_vantage_only_when_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "alpha_vantage")
    monkeypatch.setattr(
        "app.services.data_loader.settings.ALPHA_VANTAGE_API_KEY", "secret"
    )

    provider = get_market_data_provider()

    assert isinstance(provider, AlphaVantageMarketDataProvider)
    assert provider.api_key == "secret"


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported MARKET_DATA_PROVIDER"):
        get_market_data_provider("unknown")


def test_data_loader_facade_uses_configured_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "mock")

    data = DataLoader().fetch_data(
        "MSFT", start_date="2026-01-01", end_date="2026-01-02"
    )

    assert len(data) == 2
    assert data.iloc[-1]["Symbol"] == "MSFT"
