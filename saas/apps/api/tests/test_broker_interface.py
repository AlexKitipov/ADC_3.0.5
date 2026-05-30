"""Tests for broker service facades."""

from app.services.broker import MockBroker, OrderRequest


def test_mock_broker_places_and_closes_order() -> None:
    broker = MockBroker(starting_ticket=100)
    result = broker.place_order(OrderRequest(symbol="EURUSD", side="buy", volume=0.1, price=1.1))

    assert result.ticket == 100
    assert result.side == "BUY"
    assert result.status == "OPEN"
    assert result.model_dump()["symbol"] == "EURUSD"
    assert broker.get_order(100) == result

    closed = broker.close_order(100)

    assert closed is not None
    assert closed.status == "CLOSED"
    assert broker.get_order(100).status == "CLOSED"


def test_mock_broker_returns_none_for_unknown_ticket() -> None:
    broker = MockBroker()

    assert broker.get_order(999) is None
    assert broker.close_order(999) is None
