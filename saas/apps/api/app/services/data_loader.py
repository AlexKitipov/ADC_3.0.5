"""Backward-compatible facade for market OHLCV data providers."""

from __future__ import annotations

import os

import pandas as pd

from app.core.config import settings
from app.services.data import (
    AlphaVantageMarketDataProvider,
    MarketDataProvider,
    MockMarketDataProvider,
    YahooMarketDataProvider,
)

_PROVIDER_ALIASES = {
    "alpha": "alpha_vantage",
    "alphavantage": "alpha_vantage",
    "alpha-vantage": "alpha_vantage",
    "static": "mock",
}


def get_market_data_provider(provider_name: str | None = None) -> MarketDataProvider:
    """Return the active market data provider selected by configuration."""

    configured_provider = (
        provider_name
        or os.getenv("MARKET_DATA_PROVIDER")
        or settings.MARKET_DATA_PROVIDER
    )
    provider = _PROVIDER_ALIASES.get(
        configured_provider.strip().lower(), configured_provider.strip().lower()
    )

    if provider == "yahoo":
        return YahooMarketDataProvider()
    if provider == "mock":
        return MockMarketDataProvider()
    if provider == "alpha_vantage":
        return AlphaVantageMarketDataProvider(
            api_key=settings.ALPHA_VANTAGE_API_KEY or ""
        )

    raise ValueError(
        f"Unsupported MARKET_DATA_PROVIDER '{configured_provider}'. "
        "Expected one of: yahoo, alpha_vantage, mock."
    )


class DataLoader:
    """Compatibility facade for legacy callers of market data loading helpers."""

    def __init__(
        self,
        alpha_vantage_key: str | None = None,
        provider: MarketDataProvider | None = None,
    ) -> None:
        """Initialize the loader with an optional explicit provider."""

        self.alpha_vantage_key = alpha_vantage_key
        self.provider = provider

    def fetch_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch market data through the configured provider contract."""

        provider = self.provider or self._provider_for_request(timeframe)
        return provider.get_ohlcv(symbol, timeframe, start_date, end_date)

    def _provider_for_request(self, timeframe: str) -> MarketDataProvider:
        """Select a provider while preserving legacy alpha-key behavior."""

        configured_provider = os.getenv("MARKET_DATA_PROVIDER")
        if configured_provider:
            return get_market_data_provider(configured_provider)

        if timeframe != "1d":
            if not self.alpha_vantage_key:
                raise ValueError(
                    "Alpha Vantage API key required for intraday timeframes."
                )
            return AlphaVantageMarketDataProvider(api_key=self.alpha_vantage_key)

        return get_market_data_provider("yahoo")

    @staticmethod
    def normalize_price(value: float, digits: int = 5) -> float:
        """Normalize a price to the requested number of decimal places."""

        return round(value, digits)

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> bool:
        """Return whether a DataFrame contains required OHLCV columns."""

        required = {"Open", "High", "Low", "Close", "Volume"}
        return required.issubset(set(df.columns))


__all__ = ["DataLoader", "get_market_data_provider"]
