"""Technical indicator API endpoints."""

from __future__ import annotations

import math

import pandas as pd
from fastapi import APIRouter

from app.schemas import (
    IndicatorCalculationRequest,
    IndicatorCalculationResponse,
    IndicatorRow,
    IndicatorValues,
)
from core.indicators import TechnicalIndicators

router = APIRouter()


@router.post("/calculate", response_model=IndicatorCalculationResponse)
def calculate_indicators(
    payload: IndicatorCalculationRequest,
) -> IndicatorCalculationResponse:
    """Calculate technical indicators for supplied OHLCV rows.

    This endpoint is intentionally stateless: it uses only the submitted rows and
    does not read or persist simulations, signals, users, or market data.
    """

    frame = pd.DataFrame(
        [
            {
                "Timestamp": row.timestamp,
                "Symbol": row.symbol.strip().upper(),
                "Open": row.open,
                "High": row.high,
                "Low": row.low,
                "Close": row.close,
                "Volume": row.volume,
            }
            for row in payload.rows
        ]
    )

    enriched = TechnicalIndicators.add_all_indicators(
        frame,
        rsi_period=payload.parameters.rsi_period,
        macd_fast=payload.parameters.macd_fast,
        macd_slow=payload.parameters.macd_slow,
        macd_signal=payload.parameters.macd_signal,
        bb_period=payload.parameters.bollinger_period,
        bb_std=payload.parameters.bollinger_std,
        atr_period=payload.parameters.atr_period,
    )

    rows = [
        IndicatorRow(
            timestamp=pd.to_datetime(row["Timestamp"]).isoformat(),
            symbol=str(row["Symbol"]),
            close=float(row["Close"]),
            indicators=IndicatorValues(
                rsi=_nullable_float(row["RSI"]),
                macd=_nullable_float(row["MACD"]),
                macd_signal=_nullable_float(row["MACD_Signal"]),
                macd_hist=_nullable_float(row["MACD_Hist"]),
                bollinger_upper=_nullable_float(row["Bb_Upper"]),
                bollinger_middle=_nullable_float(row["Bb_Middle"]),
                bollinger_lower=_nullable_float(row["Bb_Lower"]),
                atr=_nullable_float(row["ATR"]),
                pivot=_nullable_float(row["Pivot"]),
                r1=_nullable_float(row["R1"]),
                s1=_nullable_float(row["S1"]),
                r2=_nullable_float(row["R2"]),
                s2=_nullable_float(row["S2"]),
                rsi_crosses=int(row["RSI_Crosses"]),
            ),
        )
        for _, row in enriched.iterrows()
    ]

    return IndicatorCalculationResponse(
        row_count=len(rows),
        parameters=payload.parameters,
        rows=rows,
    )


def _nullable_float(value: object) -> float | None:
    """Convert pandas/numpy numeric values into JSON-safe Python floats."""

    if value is None or pd.isna(value):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number
