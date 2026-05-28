"""Live trading-session coordinator for the ADC strategy stack.

The README describes a single object that wires together the mock broker,
reliable order manager, market stream, reinforcement-learning agent, and the
strategy callback used by the market-manager UI.  This module provides that
backend-friendly coordinator without notebook globals or ipywidgets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import inspect
import logging
import random
from typing import Any, Callable, Optional, Protocol

from app.services.market_stream import MockWebSocketClient, OutputSink
from app.services.order_management import (
    OP_BUY,
    OP_BUYLIMIT,
    OP_BUYSTOP,
    OP_SELL,
    OP_SELLLIMIT,
    OP_SELLSTOP,
    MockBrokerAPI,
    OrderManager,
)

logger = logging.getLogger(__name__)

StrategyCallback = Callable[..., Any]
ACTION_HOLD = "hold"
ACTION_BUY = "buy"
ACTION_SELL = "sell"
ACTION_CLOSE = "close"
ACTION_CLOSE_ALL = "close_all"


class RLAgent(Protocol):
    """Protocol for Stable-Baselines-like agents used by the live session."""

    def predict(self, observation: Any, deterministic: bool = True) -> Any:
        """Return an action or ``(action, state)`` for the current observation."""


@dataclass(frozen=True)
class TradingSessionConfig:
    """Configuration defaults for a live mock trading session."""

    symbol: str = "EURUSD"
    initial_price: float = 1.20000
    price_volatility: float = 0.0001
    stream_interval: float = 1.0
    order_volume: float = 0.1
    slippage: int = 5
    magic: int = 305
    broker_error_rate: float = 0.1
    broker_trade_allowed: bool = False
    retry_attempts: int = 3
    sleep_time: float = 0.1
    sleep_maximum: float = 0.5
    max_close_duration: float = 5.0
    random_seed: Optional[int] = None


@dataclass(frozen=True)
class SessionEvent:
    """Structured audit event emitted by :class:`TradingSession`."""

    type: str
    message: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    details: dict[str, Any] = field(default_factory=dict)


class TradingSession:
    """Coordinate broker, order manager, market stream, strategy, and RL agent.

    The session owns the same components that were global in the README
    notebook, but exposes them as an injectable Python service.  Ticks from the
    market stream are routed to a strategy first; if it does not produce an
    action, the optional RL agent is asked for an action.  Normalized actions are
    then executed through :class:`OrderManager` against :class:`MockBrokerAPI`.
    """

    def __init__(
        self,
        config: Optional[TradingSessionConfig] = None,
        *,
        broker_api: Optional[MockBrokerAPI] = None,
        order_manager: Optional[OrderManager] = None,
        market_stream: Optional[MockWebSocketClient] = None,
        strategy: Optional[StrategyCallback] = None,
        rl_agent: Optional[RLAgent] = None,
        output_sink: Optional[OutputSink] = None,
    ) -> None:
        """Build a fully wired live trading session.

        Args:
            config: Runtime defaults for broker, stream, and order execution.
            broker_api: Optional preconfigured broker simulation.
            order_manager: Optional order manager using ``broker_api``.
            market_stream: Optional stream; its callback is overwritten so ticks
                pass through this session.
            strategy: Optional callable/object that converts ticks to actions.
            rl_agent: Optional Stable-Baselines-like agent with ``predict``.
            output_sink: Optional notebook-like sink with ``append_stdout``.
        """

        self.config = config or TradingSessionConfig()
        self.output_sink = output_sink
        self.broker_api = broker_api or MockBrokerAPI(
            error_rate=self.config.broker_error_rate,
            trade_allowed=self.config.broker_trade_allowed,
        )
        self.order_manager = order_manager or OrderManager(
            broker_api=self.broker_api,
            retry_attempts=self.config.retry_attempts,
            sleep_time=self.config.sleep_time,
            sleep_maximum=self.config.sleep_maximum,
            max_close_duration=self.config.max_close_duration,
            on_order_closed=self.manual_order_closed_callback,
        )
        if self.order_manager.on_order_closed is None:
            self.order_manager.on_order_closed = self.manual_order_closed_callback

        self.strategy = strategy
        self.rl_agent = rl_agent
        self.events: list[SessionEvent] = []
        self.last_tick: Optional[dict[str, Any]] = None
        self.last_action: Any = None
        self.is_trading_active = False

        self.market_stream = market_stream or MockWebSocketClient(
            broker_api=self.broker_api,
            symbol=self.config.symbol,
            initial_price=self.config.initial_price,
            price_volatility=self.config.price_volatility,
            stream_interval=self.config.stream_interval,
            on_data_received=self.on_market_data,
            output_sink=self.output_sink,
            random_seed=self.config.random_seed,
        )
        self.market_stream.on_data_received = self.on_market_data

    @property
    def symbol(self) -> str:
        """Return the session's currently streamed symbol."""

        return self.market_stream.symbol

    def connect_broker(self) -> None:
        """Enable trading on the mock broker."""

        self.broker_api.set_trade_allowed(True)
        self._emit("broker_connected", "Broker connected (simulated).")

    def disconnect_broker(self) -> None:
        """Stop the stream and disable trading on the mock broker."""

        self.stop()
        self.broker_api.set_trade_allowed(False)
        self._emit("broker_disconnected", "Broker disconnected (simulated).")

    def start(self, *, connect_broker: bool = True) -> None:
        """Start the live market stream and optionally enable trading."""

        if connect_broker:
            self.connect_broker()
        if self.is_trading_active:
            self._emit("session_already_started", "Trading strategy is already running.")
            return
        self.is_trading_active = True
        self.market_stream.connect()
        self._emit("session_started", "Trading strategy STARTED.")

    def stop(self) -> None:
        """Stop the live market stream."""

        if not self.is_trading_active and not self.market_stream.is_streaming:
            return
        self.is_trading_active = False
        self.market_stream.disconnect()
        self._emit("session_stopped", "Trading strategy STOPPED.")

    def on_market_data(self, market_data: dict[str, Any]) -> Any:
        """Process one tick from the market stream and execute its action."""

        self.last_tick = market_data
        action = self._select_action(market_data)
        self.last_action = action
        normalized = self._normalize_action(action)
        if normalized in (None, ACTION_HOLD):
            self._emit("action_hold", "No trade action for tick.", action=action)
            return None
        return self.execute_action(normalized, market_data, raw_action=action)

    def execute_action(
        self,
        action: str,
        market_data: Optional[dict[str, Any]] = None,
        *,
        raw_action: Any = None,
    ) -> Any:
        """Execute a normalized strategy/RL action."""

        del market_data
        if action == ACTION_BUY:
            return self.place_market_order(OP_BUY, comment="Strategy Buy")
        if action == ACTION_SELL:
            return self.place_market_order(OP_SELL, comment="Strategy Sell")
        if action in (ACTION_CLOSE, ACTION_CLOSE_ALL):
            return self.close_all_positions(exit_reason="Strategy Close")
        self._emit(
            "action_unknown",
            f"Unknown action ignored: {action}",
            raw_action=raw_action,
        )
        return None

    def place_market_order(
        self,
        cmd: int,
        *,
        symbol: Optional[str] = None,
        volume: Optional[float] = None,
        slippage: Optional[int] = None,
        stoploss: float = 0.0,
        takeprofit: float = 0.0,
        comment: str = "Manual Order",
        magic: Optional[int] = None,
    ) -> int:
        """Place a BUY or SELL market order through the reliable manager."""

        if not self.broker_api.is_trade_allowed():
            self._emit("order_rejected", "Cannot place order: trading is not allowed.")
            return -1

        order_symbol = symbol or self.symbol
        market_info = self.broker_api.get_market_info(order_symbol)
        if cmd in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]:
            price = market_info["ask"]
            side = "BUY"
        elif cmd in [OP_SELL, OP_SELLLIMIT, OP_SELLSTOP]:
            price = market_info["bid"]
            side = "SELL"
        else:
            self._emit("order_rejected", f"Unsupported order command: {cmd}")
            return -1

        ticket = self.order_manager.send_order_reliable(
            order_symbol,
            cmd,
            volume if volume is not None else self.config.order_volume,
            price,
            slippage if slippage is not None else self.config.slippage,
            stoploss,
            takeprofit,
            comment,
            magic if magic is not None else self._next_magic(),
        )
        if ticket != -1:
            self._emit(
                "order_opened",
                f"{side} order opened: ticket {ticket}.",
                ticket=ticket,
                symbol=order_symbol,
                cmd=cmd,
                price=price,
            )
        else:
            self._emit(
                "order_failed",
                f"Failed to open {side} order.",
                error=self.order_manager.get_last_error(),
            )
        return ticket

    def close_all_positions(self, *, exit_reason: str = "Manual Close All") -> list[int]:
        """Close all currently open mock-broker positions."""

        if not self.broker_api.is_trade_allowed():
            self._emit("close_rejected", "Cannot close orders: trading is not allowed.")
            return []

        closed_tickets: list[int] = []
        open_orders = [
            (ticket, order)
            for ticket, order in self.broker_api._open_orders.items()
            if order.get("status") == "open"
        ]
        if not open_orders:
            self._emit("no_positions", "No open positions to close.")
            return closed_tickets

        for ticket, order in open_orders:
            close_price = self._closing_price(order)
            pnl = self._calculate_pnl(order, close_price)
            closed = self.order_manager.close_order_reliable(
                ticket,
                order["volume"],
                close_price,
                self.config.slippage,
                pnl=pnl,
                order_details=order.copy(),
                exit_reason=exit_reason,
            )
            if closed:
                closed_tickets.append(ticket)
                self._emit("order_closed", f"Ticket {ticket} closed.", ticket=ticket, pnl=pnl)
            else:
                self._emit(
                    "close_failed",
                    f"Failed to close ticket {ticket}.",
                    ticket=ticket,
                    error=self.order_manager.get_last_error(),
                )
        return closed_tickets

    def list_open_positions(self) -> list[dict[str, Any]]:
        """Return open positions with current price and unrealized PnL."""

        positions: list[dict[str, Any]] = []
        for order in self.broker_api._open_orders.values():
            if order.get("status") != "open":
                continue
            close_price = self._closing_price(order)
            positions.append(
                {
                    **order,
                    "current_price": close_price,
                    "unrealized_pnl": self._calculate_pnl(order, close_price),
                }
            )
        return positions

    def manual_order_closed_callback(
        self,
        ticket_id: int,
        success: bool,
        close_price: float,
        pnl: float,
        order_details: Optional[dict[str, Any]],
        exit_reason: str,
    ) -> None:
        """Default callback used by manual/session close operations."""

        event_type = "order_close_callback" if success else "order_close_failed_callback"
        message = (
            f"CALLBACK: Order {ticket_id} closed at {close_price} (PnL: {pnl:.2f})."
            if success
            else f"CALLBACK: Order {ticket_id} failed to close. Reason: {exit_reason}."
        )
        self._emit(
            event_type,
            message,
            ticket_id=ticket_id,
            success=success,
            close_price=close_price,
            pnl=pnl,
            order_details=order_details,
            exit_reason=exit_reason,
        )

    def build_observation(self, market_data: dict[str, Any]) -> dict[str, Any]:
        """Build a lightweight observation for RL agents and strategies."""

        return {
            "symbol": market_data.get("symbol", self.symbol),
            "price": market_data.get("price"),
            "bid": market_data.get("bid"),
            "ask": market_data.get("ask"),
            "open_positions": len(self.list_open_positions()),
            "trade_allowed": self.broker_api.is_trade_allowed(),
        }

    def _select_action(self, market_data: dict[str, Any]) -> Any:
        strategy_action = self._call_strategy(market_data)
        if strategy_action is not None:
            return strategy_action
        if not self.rl_agent:
            return ACTION_HOLD
        prediction = self.rl_agent.predict(self.build_observation(market_data), deterministic=True)
        if isinstance(prediction, tuple):
            return prediction[0]
        return prediction

    def _call_strategy(self, market_data: dict[str, Any]) -> Any:
        if not self.strategy:
            return None
        target = self.strategy
        for method_name in ("on_tick", "generate_signal", "decide"):
            method = getattr(self.strategy, method_name, None)
            if method:
                target = method
                break
        parameters = inspect.signature(target).parameters
        if len(parameters) >= 2:
            return target(market_data, self)
        return target(market_data)

    def _normalize_action(self, action: Any) -> Optional[str]:
        if action is None:
            return None
        if isinstance(action, dict):
            action = action.get("action", action.get("side", action.get("cmd")))
        if isinstance(action, (list, tuple)) and action:
            action = action[0]
        if hasattr(action, "item"):
            action = action.item()
        if isinstance(action, int):
            return {0: ACTION_HOLD, 1: ACTION_BUY, 2: ACTION_SELL, 3: ACTION_CLOSE}.get(action)
        if isinstance(action, str):
            normalized = action.lower().strip().replace("-", "_").replace(" ", "_")
            aliases = {
                "buy_market": ACTION_BUY,
                "long": ACTION_BUY,
                "sell_market": ACTION_SELL,
                "short": ACTION_SELL,
                "flat": ACTION_CLOSE,
                "close_positions": ACTION_CLOSE_ALL,
            }
            return aliases.get(normalized, normalized)
        return None

    def _closing_price(self, order: dict[str, Any]) -> float:
        market_info = self.broker_api.get_market_info(order["symbol"])
        if order["cmd"] in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]:
            return market_info["bid"]
        return market_info["ask"]

    def _calculate_pnl(self, order: dict[str, Any], close_price: float) -> float:
        if order["cmd"] in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]:
            return (close_price - order["open_price"]) * order["volume"]
        if order["cmd"] in [OP_SELL, OP_SELLLIMIT, OP_SELLSTOP]:
            return (order["open_price"] - close_price) * order["volume"]
        return 0.0

    def _next_magic(self) -> int:
        if self.config.random_seed is None:
            return random.randint(1000, 9999)
        return self.config.magic

    def _emit(self, event_type: str, message: str, **details: Any) -> None:
        event = SessionEvent(type=event_type, message=message, details=details)
        self.events.append(event)
        logger.info(message)
        if self.output_sink:
            self.output_sink.append_stdout(f"{message}\n")


def create_trading_session(**kwargs: Any) -> TradingSession:
    """Factory helper mirroring the README's global ``trading_session`` object."""

    return TradingSession(**kwargs)
