"""Tests for the broker simulation and reliable order manager."""

from app.services.order_management import (
    ERR_INVALID_TICKET,
    ERR_NO_ERROR,
    ERR_TRADE_DISABLED,
    OP_BUY,
    MockBrokerAPI,
    OrderManager,
    ensure_valid_stop_level,
)


def test_send_order_reliable_opens_order_when_trading_is_allowed() -> None:
    broker = MockBrokerAPI(trade_allowed=True)
    manager = OrderManager(broker, sleep_time=0, sleep_maximum=0)
    market_info = broker.get_market_info("EURUSD")

    ticket = manager.send_order_reliable(
        "EURUSD",
        OP_BUY,
        0.1,
        market_info["ask"],
        50,
        market_info["ask"] - 0.01,
        market_info["ask"] + 0.01,
        "unit-test",
        123,
    )

    assert ticket == 100000
    assert broker._open_orders[ticket]["status"] == "open"
    assert manager.get_last_error() == ERR_NO_ERROR


def test_send_order_reliable_returns_minus_one_when_trading_is_disabled() -> None:
    broker = MockBrokerAPI(trade_allowed=False)
    manager = OrderManager(broker, sleep_time=0, sleep_maximum=0)
    market_info = broker.get_market_info("EURUSD")

    ticket = manager.send_order_reliable(
        "EURUSD", OP_BUY, 0.1, market_info["ask"], 50, 0, 0, "disabled", 123
    )

    assert ticket == -1
    assert manager.get_last_error() == ERR_TRADE_DISABLED


def test_close_order_reliable_updates_status_and_invokes_callback() -> None:
    callbacks = []
    broker = MockBrokerAPI(trade_allowed=True)
    manager = OrderManager(
        broker,
        sleep_time=0,
        sleep_maximum=0,
        on_order_closed=lambda *args: callbacks.append(args),
    )
    market_info = broker.get_market_info("EURUSD")
    ticket = manager.send_order_reliable(
        "EURUSD", OP_BUY, 0.1, market_info["ask"], 50, 0, 0, "close-test", 123
    )

    close_bid = broker.get_market_info("EURUSD")["bid"]
    closed = manager.close_order_reliable(
        ticket,
        0.1,
        close_bid,
        50,
        pnl=12.5,
        order_details={"symbol": "EURUSD"},
        exit_reason="target",
    )

    assert closed is True
    assert broker._open_orders[ticket]["status"] == "closed"
    assert callbacks == [
        (ticket, True, close_bid, 12.5, {"symbol": "EURUSD"}, "target")
    ]


def test_close_order_reliable_reports_invalid_ticket() -> None:
    callbacks = []
    broker = MockBrokerAPI(trade_allowed=True)
    manager = OrderManager(
        broker,
        sleep_time=0,
        sleep_maximum=0,
        on_order_closed=lambda *args: callbacks.append(args),
    )

    closed = manager.close_order_reliable(999, 0.1, 1.0, 10)

    assert closed is False
    assert manager.get_last_error() == ERR_INVALID_TICKET
    assert callbacks == [(999, False, 1.0, 0.0, None, "")]


def test_ensure_valid_stop_level_respects_minimum_distance() -> None:
    market_info = {"MODE_STOPLEVEL": 20, "MODE_POINT": 0.00001, "MODE_DIGITS": 5}

    adjusted = ensure_valid_stop_level("EURUSD", 1.1, 1.09995, True, market_info)

    assert adjusted == 1.0998
