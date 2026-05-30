"""Technical indicator API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.market_data import OHLCVRow

IndicatorCalculationMode = Literal["stateless"]


class IndicatorParameters(BaseModel):
    """Lookback and smoothing parameters for technical indicator calculations."""

    rsi_period: int = Field(default=14, ge=2, le=200)
    macd_fast: int = Field(default=12, ge=2, le=200)
    macd_slow: int = Field(default=26, ge=3, le=300)
    macd_signal: int = Field(default=9, ge=2, le=200)
    bollinger_period: int = Field(default=20, ge=2, le=300)
    bollinger_std: float = Field(default=2.0, gt=0, le=10)
    atr_period: int = Field(default=14, ge=2, le=200)

    @model_validator(mode="after")
    def validate_macd_windows(self) -> "IndicatorParameters":
        """Ensure the MACD slow window is larger than the fast window."""

        if self.macd_fast >= self.macd_slow:
            raise ValueError("macd_fast must be less than macd_slow")
        return self


class IndicatorCalculationRequest(BaseModel):
    """Stateless OHLCV input for technical indicator calculations."""

    rows: list[OHLCVRow] = Field(..., min_length=1)
    parameters: IndicatorParameters = Field(default_factory=IndicatorParameters)

    @model_validator(mode="after")
    def validate_enough_rows_for_windows(self) -> "IndicatorCalculationRequest":
        """Require enough rows for the largest requested rolling window."""

        required_rows = max(
            self.parameters.rsi_period,
            self.parameters.macd_slow,
            self.parameters.bollinger_period,
            self.parameters.atr_period,
        )
        if len(self.rows) < required_rows:
            raise ValueError(
                f"at least {required_rows} OHLCV rows are required "
                "for the requested indicator windows"
            )
        return self


class IndicatorValues(BaseModel):
    """Computed technical indicator values for one OHLCV row."""

    rsi: float | None
    macd: float | None
    macd_signal: float | None
    macd_hist: float | None
    bollinger_upper: float | None
    bollinger_middle: float | None
    bollinger_lower: float | None
    atr: float | None
    pivot: float | None
    r1: float | None
    s1: float | None
    r2: float | None
    s2: float | None
    rsi_crosses: int


class IndicatorRow(BaseModel):
    """OHLCV row metadata paired with computed indicator values."""

    timestamp: str
    symbol: str
    close: float
    indicators: IndicatorValues


class IndicatorCalculationResponse(BaseModel):
    """Envelope for calculated indicator rows and contract metadata."""

    calculation_mode: IndicatorCalculationMode = "stateless"
    row_count: int
    parameters: IndicatorParameters
    rows: list[IndicatorRow]


__all__ = [
    "IndicatorCalculationMode",
    "IndicatorCalculationRequest",
    "IndicatorCalculationResponse",
    "IndicatorParameters",
    "IndicatorRow",
    "IndicatorValues",
]
