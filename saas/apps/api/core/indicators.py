"""Technical analysis indicators module.

Computes RSI, MACD, Bollinger Bands, ATR, and Pivot Points.
"""

from typing import Tuple

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange, BollingerBands


class TechnicalIndicators:
    """Computes technical analysis indicators on OHLCV data."""

    @staticmethod
    def calculate_rsi(
        close: pd.Series, period: int = 14, fillna: bool = True
    ) -> pd.Series:
        """Calculate Relative Strength Index.

        Args:
            close: Close price series.
            period: RSI lookback period.
            fillna: If True, fill NaN values with 0.

        Returns:
            RSI values.
        """
        rsi = RSIIndicator(close=close, window=period, fillna=fillna)
        return rsi.rsi()

    @staticmethod
    def calculate_macd(
        close: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        fillna: bool = True,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator.

        Args:
            close: Close price series.
            fast: Fast EMA period.
            slow: Slow EMA period.
            signal: Signal line EMA period.
            fillna: If True, fill NaN values.

        Returns:
            Tuple of (MACD line, Signal line, Histogram).
        """
        macd = MACD(
            close=close,
            window_fast=fast,
            window_slow=slow,
            window_sign=signal,
            fillna=fillna,
        )
        return macd.macd(), macd.macd_signal(), macd.macd_diff()

    @staticmethod
    def calculate_bollinger_bands(
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
        fillna: bool = True,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands.

        Args:
            close: Close price series.
            period: MA lookback period.
            std_dev: Standard deviation multiplier.
            fillna: If True, fill NaN values.

        Returns:
            Tuple of (Upper band, Middle band, Lower band).
        """
        bb = BollingerBands(
            close=close, window=period, window_dev=std_dev, fillna=fillna
        )
        return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        fillna: bool = True,
    ) -> pd.Series:
        """Calculate Average True Range.

        Args:
            high: High price series.
            low: Low price series.
            close: Close price series.
            period: ATR lookback period.
            fillna: If True, fill NaN values.

        Returns:
            ATR values.
        """
        atr = AverageTrueRange(
            high=high, low=low, close=close, window=period, fillna=fillna
        )
        return atr.average_true_range()

    @staticmethod
    def calculate_pivots(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate pivot levels (Standard Pivot Points).

        Pivot = (H + L + C) / 3
        R1 = 2 * Pivot - L
        S1 = 2 * Pivot - H
        R2 = Pivot + (H - L)
        S2 = Pivot - (H - L)

        Args:
            df: DataFrame with High, Low, Close columns.

        Returns:
            DataFrame with added Pivot, R1, S1, R2, S2 columns.
        """
        df = df.copy()
        df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
        df["R1"] = 2 * df["Pivot"] - df["Low"]
        df["S1"] = 2 * df["Pivot"] - df["High"]
        df["R2"] = df["Pivot"] + (df["High"] - df["Low"])
        df["S2"] = df["Pivot"] - (df["High"] - df["Low"])
        return df

    @staticmethod
    def count_rsi_crosses(
        rsi: pd.Series, upper: int = 70, lower: int = 30, window: int = 20
    ) -> list[int]:
        """Count RSI values outside overbought/oversold levels in a rolling window.

        Args:
            rsi: RSI series.
            upper: Overbought threshold.
            lower: Oversold threshold.
            window: Rolling window size.

        Returns:
            List of threshold breach counts for each row.
        """
        crosses = []
        for i in range(len(rsi)):
            if i < window:
                crosses.append(0)
            else:
                window_rsi = rsi.iloc[i - window : i].dropna()
                count = ((window_rsi > upper) | (window_rsi < lower)).sum()
                crosses.append(int(count))
        return crosses

    @staticmethod
    def add_all_indicators(
        df: pd.DataFrame,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        atr_period: int = 14,
    ) -> pd.DataFrame:
        """Add all technical indicators to DataFrame in one call.

        Args:
            df: Input DataFrame with OHLCV data.
            rsi_period: RSI period.
            macd_fast: MACD fast EMA.
            macd_slow: MACD slow EMA.
            macd_signal: MACD signal line.
            bb_period: Bollinger Bands period.
            bb_std: Bollinger Bands std dev.
            atr_period: ATR period.

        Returns:
            DataFrame with all indicators added.
        """
        df = df.copy()

        df = TechnicalIndicators.calculate_pivots(df)
        df["RSI"] = TechnicalIndicators.calculate_rsi(df["Close"], rsi_period)

        macd_line, macd_signal_line, macd_hist = TechnicalIndicators.calculate_macd(
            df["Close"], macd_fast, macd_slow, macd_signal
        )
        df["MACD"] = macd_line
        df["MACD_Signal"] = macd_signal_line
        df["MACD_Hist"] = macd_hist

        bb_upper, bb_mid, bb_lower = TechnicalIndicators.calculate_bollinger_bands(
            df["Close"], bb_period, bb_std
        )
        df["Bb_Upper"] = bb_upper
        df["Bb_Middle"] = bb_mid
        df["Bb_Lower"] = bb_lower

        df["ATR"] = TechnicalIndicators.calculate_atr(
            df["High"], df["Low"], df["Close"], atr_period
        )
        df["RSI_Crosses"] = TechnicalIndicators.count_rsi_crosses(df["RSI"])

        return df
