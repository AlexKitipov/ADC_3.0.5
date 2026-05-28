"""Tests for technical indicator helpers."""

import pandas as pd

from core.indicators import TechnicalIndicators


def sample_ohlcv(rows: int = 40) -> pd.DataFrame:
    """Build deterministic OHLCV data for indicator tests."""

    close = pd.Series([100 + index for index in range(rows)], dtype="float64")
    return pd.DataFrame(
        {
            "Open": close - 0.25,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": [1000 + index for index in range(rows)],
        }
    )


def test_calculate_pivots_adds_standard_levels_without_mutating_input() -> None:
    data = pd.DataFrame({"High": [12.0], "Low": [6.0], "Close": [9.0]})

    result = TechnicalIndicators.calculate_pivots(data)

    assert "Pivot" not in data.columns
    assert result.loc[0, "Pivot"] == 9.0
    assert result.loc[0, "R1"] == 12.0
    assert result.loc[0, "S1"] == 6.0
    assert result.loc[0, "R2"] == 15.0
    assert result.loc[0, "S2"] == 3.0


def test_count_rsi_crosses_counts_threshold_breaches_in_prior_window() -> None:
    rsi = pd.Series([50, 75, 20, 55, 80, 10], dtype="float64")

    crosses = TechnicalIndicators.count_rsi_crosses(
        rsi, upper=70, lower=30, window=3
    )

    assert crosses == [0, 0, 0, 2, 2, 2]


def test_add_all_indicators_adds_expected_columns_and_preserves_input() -> None:
    data = sample_ohlcv()

    result = TechnicalIndicators.add_all_indicators(data)

    expected_columns = {
        "Pivot",
        "R1",
        "S1",
        "R2",
        "S2",
        "RSI",
        "MACD",
        "MACD_Signal",
        "MACD_Hist",
        "Bb_Upper",
        "Bb_Middle",
        "Bb_Lower",
        "ATR",
        "RSI_Crosses",
    }
    assert expected_columns.issubset(result.columns)
    assert expected_columns.isdisjoint(data.columns)
    assert len(result) == len(data)
