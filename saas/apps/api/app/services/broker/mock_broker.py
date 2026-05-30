"""Deterministic in-memory broker adapter."""

from __future__ import annotations

from app.services.broker.base import OrderRequest, OrderResult


class MockBroker:
    """Minimal broker facade used for tests and future endpoint wiring."""

    def __init__(self, starting_ticket: int = 1) -> None:
        self._next_ticket = starting_ticket
        self._orders: dict[int, OrderResult] = {}

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Place an order in memory and return a deterministic ticket."""

        result = OrderResult(
            ticket=self._next_ticket,
            symbol=request.symbol,
            side=request.side.upper(),
            volume=request.volume,
            status="OPEN",
            price=request.price,
        )
        self._orders[result.ticket] = result
        self._next_ticket += 1
        return result

    def get_order(self, ticket: int) -> OrderResult | None:
        """Return an order by ticket, if it exists."""

        return self._orders.get(ticket)

    def close_order(self, ticket: int) -> OrderResult | None:
        """Mark an existing in-memory order as closed."""

        order = self._orders.get(ticket)
        if order is None:
            return None

        closed = OrderResult(
            ticket=order.ticket,
            symbol=order.symbol,
            side=order.side,
            volume=order.volume,
            status="CLOSED",
            price=order.price,
        )
        self._orders[ticket] = closed
        return closed


__all__ = ["MockBroker"]
