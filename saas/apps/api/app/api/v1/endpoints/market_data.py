"""Market data API endpoints."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.schemas import MarketDataResponse, MarketDataTimeframe, OHLCVRow
from app.services.data_loader import DataLoader

router = APIRouter()


@router.get("/ohlcv", response_model=MarketDataResponse)
def get_ohlcv_market_data(
    symbol: Annotated[str, Query(min_length=1, max_length=32)],
    timeframe: MarketDataTimeframe = "1d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> MarketDataResponse:
    """Return standardized OHLCV market rows for preview and setup flows."""

    normalized_symbol = symbol.strip().upper()
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be before or equal to end_date",
        )

    loader = DataLoader(alpha_vantage_key=settings.ALPHA_VANTAGE_API_KEY)
    try:
        data = loader.fetch_data(
            normalized_symbol,
            timeframe=timeframe,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
        )
    except ValueError as exc:
        message = str(exc)
        if "Alpha Vantage API key required" in message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alpha Vantage API key is required for intraday timeframes.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message,
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    rows = _dataframe_to_rows(data, normalized_symbol)
    return MarketDataResponse(
        symbol=normalized_symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        rows=rows,
        row_count=len(rows),
    )


def _dataframe_to_rows(data: pd.DataFrame, symbol: str) -> list[OHLCVRow]:
    """Convert a standardized OHLCV DataFrame into API row models."""

    rows: list[OHLCVRow] = []
    for index, row in data.iterrows():
        timestamp = pd.to_datetime(index).to_pydatetime()
        if isinstance(timestamp, date) and not isinstance(timestamp, datetime):
            timestamp = datetime.combine(timestamp, time.min)

        rows.append(
            OHLCVRow(
                timestamp=timestamp,
                symbol=str(row.get("Symbol", symbol)),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )
    return rows
