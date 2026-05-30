"""Broker client interface primitives for execution adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from app.schemas.orders import OrderClose, OrderCreate

BrokerOrder = dict[str, Any]
BrokerAccountSnapshot = dict[str, Any]


@dataclass(frozen=True)
class OrderRequest:
    """Serializable legacy order-placement request DTO."""

    symbol: str
    side: str
    volume: float
    price: float | None = None

    def model_dump(self) -> dict:
        """Return a Pydantic-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class OrderResult:
    """Serializable legacy order result DTO."""

    ticket: int
    symbol: str
    side: str
    volume: float
    status: str
    price: float | None = None

    def model_dump(self) -> dict:
        """Return a Pydantic-compatible representation."""

        return asdict(self)


class BrokerClient(Protocol):
    """Protocol implemented by broker execution adapters."""

    def place_order(self, order: OrderCreate) -> BrokerOrder:
        """Place an order and return broker-native execution metadata."""

    def close_order(self, ticket: int, order_close: OrderClose) -> BrokerOrder:
        """Close an existing order and return broker-native execution metadata."""

    def get_open_orders(self) -> list[BrokerOrder]:
        """Return broker-native open orders."""

    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        """Return broker account metadata suitable for health/status checks."""

    def get_order(self, ticket: int) -> BrokerOrder | None:
        """Return a broker-native order by ticket, if known."""

    def get_last_error(self) -> int:
        """Return the last broker error code."""


class Broker(Protocol):
    """Legacy minimal broker facade protocol."""

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Place an order and return broker execution metadata."""

    def get_order(self, ticket: int) -> OrderResult | None:
        """Return an order by ticket, if known."""

    def close_order(self, ticket: int) -> OrderResult | None:
        """Close an existing order, if known."""


__all__ = [
    "Broker",
    "BrokerAccountSnapshot",
    "BrokerClient",
    "BrokerOrder",
    "OrderRequest",
    "OrderResult",
]
