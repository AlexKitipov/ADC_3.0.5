"""Tests for the live trading-session coordinator."""

from app.services.order_management import OP_BUY, OP_SELL, MockBrokerAPI
from app.services.trading_session import TradingSession, TradingSessionConfig


class OutputBuffer:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def append_stdout(self, text: str) -> None:
        self.lines.append(text)


def make_session(strategy=None, rl_agent=None) -> TradingSession:
    return TradingSession(
        TradingSessionConfig(
            broker_error_rate=0.0,
            broker_trade_allowed=True,
            sleep_time=0,
            sleep_maximum=0,
            max_close_duration=0.25,
            random_seed=7,
        ),
        strategy=strategy,
        rl_agent=rl_agent,
    )


def test_strategy_tick_opens_buy_order() -> None:
    session = make_session(strategy=lambda tick, session: "buy")

    ticket = session.on_market_data(
        {"symbol": "EURUSD", "price": 1.2, "bid": 1.19995, "ask": 1.20005}
    )

    assert ticket == 100000
    assert session.broker_api._open_orders[ticket]["cmd"] == OP_BUY
    assert session.last_action == "buy"
    assert session.events[-1].type == "order_opened"


def test_rl_agent_is_used_when_strategy_holds() -> None:
    class Agent:
        def __init__(self) -> None:
            self.observation = None

        def predict(self, observation, deterministic=True):
            self.observation = observation
            return 2, None

    agent = Agent()
    session = make_session(rl_agent=agent)

    ticket = session.on_market_data(
        {"symbol": "EURUSD", "price": 1.2, "bid": 1.19995, "ask": 1.20005}
    )

    assert ticket == 100000
    assert agent.observation["symbol"] == "EURUSD"
    assert session.broker_api._open_orders[ticket]["cmd"] == OP_SELL


def test_close_all_positions_closes_only_open_orders() -> None:
    session = make_session()
    buy_ticket = session.place_market_order(OP_BUY)
    sell_ticket = session.place_market_order(OP_SELL)

    closed = session.close_all_positions(exit_reason="unit test")

    assert closed == [buy_ticket, sell_ticket]
    assert session.broker_api._open_orders[buy_ticket]["status"] == "closed"
    assert session.broker_api._open_orders[sell_ticket]["status"] == "closed"
    assert session.list_open_positions() == []


def test_broker_connection_and_output_sink_are_coordinated() -> None:
    output = OutputBuffer()
    broker = MockBrokerAPI(trade_allowed=False)
    session = TradingSession(
        TradingSessionConfig(stream_interval=0, broker_error_rate=0.0),
        broker_api=broker,
        output_sink=output,
    )

    session.connect_broker()
    session.start(connect_broker=False)
    session.stop()
    session.disconnect_broker()

    assert broker.is_trade_allowed() is False
    assert any("Broker connected" in line for line in output.lines)
    assert any(event.type == "session_started" for event in session.events)
    assert any(event.type == "session_stopped" for event in session.events)
