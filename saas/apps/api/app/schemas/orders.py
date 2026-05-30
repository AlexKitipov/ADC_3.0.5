"""Executable broker order request and response schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderType(StrEnum):
    """Supported MQL4-style order directions and pending order types."""

    BUY = "BUY"
    SELL = "SELL"
    BUYSTOP = "BUYSTOP"
    SELLSTOP = "SELLSTOP"
    BUYLIMIT = "BUYLIMIT"
    SELLLIMIT = "SELLLIMIT"


class OrderCreate(BaseModel):
    """Payload for submitting a manual broker order.

    These orders are routed to the in-memory mock broker and are intentionally
    separate from persisted ``Trade`` journal rows.
    """

    symbol: str = Field(min_length=1, max_length=32)
    order_type: OrderType
    volume: float = Field(gt=0)
    price: float = Field(gt=0)
    stop_loss: float = Field(default=0.0, ge=0)
    take_profit: float = Field(default=0.0, ge=0)
    slippage: int = Field(default=3, ge=0, le=1000)
    comment: str = Field(default="manual-order", max_length=128)
    magic: int = Field(default=0, ge=0)


class OrderClose(BaseModel):
    """Payload for closing a manual broker order."""

    volume: float | None = Field(default=None, gt=0)
    price: float = Field(gt=0)
    slippage: int = Field(default=3, ge=0, le=1000)
    exit_reason: str = Field(default="manual-close", max_length=128)


class BrokerResult(BaseModel):
    """Broker execution result metadata."""

    status: str
    error_code: int = 0
    message: str


class Order(BaseModel):
    """Broker order response."""

    ticket: int
    symbol: str
    order_type: OrderType
    volume: float
    price: float
    stop_loss: float
    take_profit: float
    slippage: int | None = None
    status: str
    broker_result: BrokerResult
    open_time: datetime
    close_price: float | None = None
    close_time: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


__all__ = ["BrokerResult", "Order", "OrderClose", "OrderCreate", "OrderType"]
