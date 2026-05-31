"""Rule-level tests for deterministic provider-backed signal generation."""

from __future__ import annotations

import pandas as pd

from app.services import signal_engine
from app.services.signal_engine import generate_signal


class StaticMarketDataProvider:
    """Small provider stub returning test-controlled OHLCV rows."""

    def __init__(self, rows: int = 40) -> None:
        self.rows = rows

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        values = list(range(self.rows))
        return pd.DataFrame(
            {
                "Open": [100.0 + value for value in values],
                "High": [101.0 + value for value in values],
                "Low": [99.0 + value for value in values],
                "Close": [100.5 + value for value in values],
                "Volume": [1_000 + value for value in values],
            }
        )


def _patch_indicators(
    monkeypatch,
    *,
    rsi: float,
    macd_previous: float,
    macd_current: float,
    hist_previous: float,
    hist_current: float,
    atr: float = 1.0,
) -> None:
    def calculate_rsi(
        close: pd.Series,
        period: int = 14,
        fillna: bool = True,
    ) -> pd.Series:
        return pd.Series([50.0] * (len(close) - 1) + [rsi])

    def calculate_macd(
        close: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        fillna: bool = True,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        base = [0.0] * (len(close) - 2)
        return (
            pd.Series(base + [macd_previous, macd_current]),
            pd.Series(base + [0.0, 0.0]),
            pd.Series(base + [hist_previous, hist_current]),
        )

    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        fillna: bool = True,
    ) -> pd.Series:
        return pd.Series([atr] * len(close))

    monkeypatch.setattr(
        signal_engine.TechnicalIndicators,
        "calculate_rsi",
        calculate_rsi,
    )
    monkeypatch.setattr(
        signal_engine.TechnicalIndicators,
        "calculate_macd",
        calculate_macd,
    )
    monkeypatch.setattr(
        signal_engine.TechnicalIndicators,
        "calculate_atr",
        calculate_atr,
    )


def test_generate_signal_returns_buy_when_oversold_and_macd_improves(monkeypatch) -> None:
    _patch_indicators(
        monkeypatch,
        rsi=24.0,
        macd_previous=-1.2,
        macd_current=-0.8,
        hist_previous=-0.35,
        hist_current=-0.1,
    )

    decision = generate_signal("eurusd", "1d", {}, StaticMarketDataProvider())

    assert decision.symbol == "EURUSD"
    assert decision.action == "BUY"
    assert 0.0 <= decision.confidence <= 1.0
    assert "RSI 24.0" in decision.explanation
    assert "improving" in decision.explanation
    assert decision.metadata["engine"] == "deterministic_rules_v1"


def test_generate_signal_returns_sell_when_overbought_and_macd_weakens(monkeypatch) -> None:
    _patch_indicators(
        monkeypatch,
        rsi=76.0,
        macd_previous=1.2,
        macd_current=0.8,
        hist_previous=0.35,
        hist_current=0.1,
    )

    decision = generate_signal("aapl", "1d", {}, StaticMarketDataProvider())

    assert decision.symbol == "AAPL"
    assert decision.action == "SELL"
    assert 0.0 <= decision.confidence <= 1.0
    assert "RSI 76.0" in decision.explanation
    assert "weakening" in decision.explanation


def test_generate_signal_defaults_to_hold_for_neutral_conditions(monkeypatch) -> None:
    _patch_indicators(
        monkeypatch,
        rsi=52.0,
        macd_previous=0.8,
        macd_current=1.1,
        hist_previous=0.1,
        hist_current=0.3,
    )

    decision = generate_signal("msft", "1d", {}, StaticMarketDataProvider())

    assert decision.action == "HOLD"
    assert 0.0 <= decision.confidence <= 1.0
    assert "do not align" in decision.explanation


def test_generate_signal_returns_safe_hold_for_short_data() -> None:
    decision = generate_signal("btc-usd", "1d", {}, StaticMarketDataProvider(rows=3))

    assert decision.symbol == "BTC-USD"
    assert decision.action == "HOLD"
    assert decision.confidence == 0.0
    assert decision.metadata["safe_default"] is True
    assert "Insufficient OHLCV history" in decision.explanation
