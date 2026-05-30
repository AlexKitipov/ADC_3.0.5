"""Broker interface primitives for the broker bounded context."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class OrderRequest:
    """Serializable order-placement request DTO."""

    symbol: str
    side: str
    volume: float
    price: float | None = None

    def model_dump(self) -> dict:
        """Return a Pydantic-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class OrderResult:
    """Serializable order result DTO."""

    ticket: int
    symbol: str
    side: str
    volume: float
    status: str
    price: float | None = None

    def model_dump(self) -> dict:
        """Return a Pydantic-compatible representation."""

        return asdict(self)


class Broker(Protocol):
    """Protocol implemented by broker adapters."""

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Place an order and return broker execution metadata."""

    def get_order(self, ticket: int) -> OrderResult | None:
        """Return an order by ticket, if known."""

    def close_order(self, ticket: int) -> OrderResult | None:
        """Close an existing order, if known."""


__all__ = ["Broker", "OrderRequest", "OrderResult"]
