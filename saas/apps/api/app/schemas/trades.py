"""Trade request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TradeCreate(BaseModel):
    """Payload for opening a simple persisted trade record."""

    symbol: str = Field(min_length=1, max_length=32)
    entry_price: float = Field(gt=0)


class TradeClose(BaseModel):
    """Payload for closing a simple persisted trade record."""

    exit_price: float = Field(gt=0)


class Trade(BaseModel):
    """Trade response."""

    id: int
    symbol: str
    entry_price: float
    exit_price: float | None
    entry_time: datetime
    exit_time: datetime | None
    pnl: float | None
    pnl_percent: float | None
    status: str

    model_config = ConfigDict(from_attributes=True)


__all__ = ["Trade", "TradeClose", "TradeCreate"]
