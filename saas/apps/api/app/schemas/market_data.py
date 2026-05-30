"""Market data API schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MarketDataTimeframe = Literal["1d", "1min", "5min", "15min", "30min", "60min"]


class MarketTickSchema(BaseModel):
    """Contract for one live market stream tick."""

    symbol: str = Field(..., min_length=1, max_length=32)
    price: float
    bid: float
    ask: float
    timestamp: datetime

    @field_validator("symbol")
    @classmethod
    def normalize_tick_symbol(cls, value: str) -> str:
        """Normalize streamed symbols for frontend consumers."""

        return value.strip().upper()


class MarketDataQuery(BaseModel):
    """Query parameters for OHLCV market data previews."""

    symbol: str = Field(..., min_length=1, max_length=32)
    timeframe: MarketDataTimeframe = "1d"
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols for provider calls and response metadata."""

        return value.strip().upper()

    @model_validator(mode="after")
    def validate_date_range(self) -> "MarketDataQuery":
        """Ensure date ranges are chronologically valid."""

        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class OHLCVRow(BaseModel):
    """One standardized OHLCV row returned from a market data provider."""

    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataResponse(BaseModel):
    """OHLCV response envelope with request metadata."""

    symbol: str
    timeframe: MarketDataTimeframe
    start_date: date | None = None
    end_date: date | None = None
    rows: list[OHLCVRow]
    row_count: int


__all__ = ["MarketDataQuery", "MarketDataResponse", "MarketDataTimeframe", "OHLCVRow"]
