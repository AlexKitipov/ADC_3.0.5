"""Mock broker execution adapter."""

from __future__ import annotations

from datetime import datetime
import random
from typing import Any

from app.schemas.orders import OrderClose, OrderCreate, OrderType
from app.services.broker.base import (
    BrokerAccountSnapshot,
    BrokerOrder,
    OrderRequest,
    OrderResult,
)
from app.services.broker.mql4 import (
    ERR_COMMON_ERROR,
    ERR_INVALID_STOPS,
    ERR_INVALID_TICKET,
    ERR_INVALID_TRADE_PARAMETERS,
    ERR_MALFUNCTIONAL_TRADE,
    ERR_NO_ERROR,
    ERR_PRICE_CHANGED,
    ERR_REQUOTE,
    ERR_SERVER_BUSY,
    ERR_TRADE_DISABLED,
    OP_BUY,
    OP_BUYLIMIT,
    OP_BUYSTOP,
    OP_SELL,
    OP_SELLLIMIT,
    OP_SELLSTOP,
    _normalize_double,
    ensure_valid_stop_level,
)

_ORDER_TYPE_TO_CMD = {
    OrderType.BUY: OP_BUY,
    OrderType.SELL: OP_SELL,
    OrderType.BUYSTOP: OP_BUYSTOP,
    OrderType.SELLSTOP: OP_SELLSTOP,
    OrderType.BUYLIMIT: OP_BUYLIMIT,
    OrderType.SELLLIMIT: OP_SELLLIMIT,
}


class MockBrokerAPI:
    """Simulate a broker API with order management and market data."""

    def __init__(self, error_rate: float = 0.0, trade_allowed: bool = False) -> None:
        """Initialize the mock broker.

        Args:
            error_rate: Probability of random order rejection from 0.0 to 1.0.
            trade_allowed: Whether trading is enabled for the broker instance.
        """

        self._trade_allowed = trade_allowed
        self._open_orders: dict[int, dict[str, Any]] = {}
        self._next_ticket = 100000
        self._market_data = {
            "EURUSD": {
                "bid": 1.08500,
                "ask": 1.08510,
                "MODE_POINT": 0.00001,
                "MODE_STOPLEVEL": 20,
                "MODE_DIGITS": 5,
            },
            "TSLA": {
                "bid": 200.00,
                "ask": 200.10,
                "MODE_POINT": 0.01,
                "MODE_STOPLEVEL": 1,
                "MODE_DIGITS": 2,
            },
        }
        self.error_rate = error_rate
        self._last_error = ERR_NO_ERROR

    def get_market_info(self, symbol: str) -> dict[str, Any]:
        """Get market info for a symbol."""

        self.refresh_rates(symbol)
        return self._market_data.get(
            symbol,
            {
                "bid": 0.0,
                "ask": 0.0,
                "MODE_POINT": 0.00001,
                "MODE_STOPLEVEL": 20,
                "MODE_DIGITS": 5,
            },
        )

    def is_trade_allowed(self) -> bool:
        """Check if trading is allowed."""

        return self._trade_allowed

    def set_trade_allowed(self, trade_allowed: bool) -> None:
        """Enable or disable trading for the mock broker."""

        self._trade_allowed = trade_allowed

    def refresh_rates(self, symbol: str) -> None:
        """Simulate price fluctuations."""

        if symbol not in self._market_data:
            return

        data = self._market_data[symbol]
        digits = data.get("MODE_DIGITS", 5)
        fluctuation = (
            random.uniform(-0.0001, 0.0001)
            if digits == 5
            else random.uniform(-0.01, 0.01)
        )
        data["bid"] = _normalize_double(data["bid"] + fluctuation, digits)
        data["ask"] = _normalize_double(data["ask"] + fluctuation, digits)
        if data["ask"] <= data["bid"]:
            data["ask"] = _normalize_double(data["bid"] + data["MODE_POINT"], digits)

    def send_order(
        self,
        symbol: str,
        cmd: int,
        volume: float,
        price: float,
        slippage: int,
        stoploss: float,
        takeprofit: float,
        comment: str,
        magic: int,
    ) -> int:
        """Send an order to the broker and return a ticket or ``-1``."""

        if not self._trade_allowed:
            self._last_error = ERR_TRADE_DISABLED
            return -1

        if random.random() < self.error_rate:
            self._last_error = random.choice(
                [
                    ERR_COMMON_ERROR,
                    ERR_SERVER_BUSY,
                    ERR_PRICE_CHANGED,
                    ERR_INVALID_TRADE_PARAMETERS,
                ]
            )
            return -1

        market_info = self.get_market_info(symbol)
        digits = market_info.get("MODE_DIGITS", 5)
        point = market_info.get("MODE_POINT", 0.00001)

        actual_price = price
        if cmd in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]:
            if actual_price < market_info["ask"] - slippage * point:
                self._last_error = ERR_REQUOTE
                return -1
            actual_price = _normalize_double(
                max(actual_price, market_info["ask"] - slippage * point), digits
            )
        elif cmd in [OP_SELL, OP_SELLLIMIT, OP_SELLSTOP]:
            if actual_price > market_info["bid"] + slippage * point:
                self._last_error = ERR_REQUOTE
                return -1
            actual_price = _normalize_double(
                min(actual_price, market_info["bid"] + slippage * point), digits
            )

        is_buy = cmd in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]
        stoploss = ensure_valid_stop_level(
            symbol, actual_price, stoploss, is_buy, market_info
        )
        takeprofit = ensure_valid_stop_level(
            symbol, actual_price, takeprofit, is_buy, market_info
        )

        if (stoploss != 0 and is_buy and stoploss >= actual_price) or (
            stoploss != 0 and not is_buy and stoploss <= actual_price
        ):
            self._last_error = ERR_INVALID_STOPS
            return -1
        if (takeprofit != 0 and is_buy and takeprofit <= actual_price) or (
            takeprofit != 0 and not is_buy and takeprofit >= actual_price
        ):
            self._last_error = ERR_INVALID_STOPS
            return -1

        ticket = self._next_ticket
        self._next_ticket += 1
        self._open_orders[ticket] = {
            "ticket": ticket,
            "symbol": symbol,
            "cmd": cmd,
            "volume": volume,
            "open_price": actual_price,
            "sl": stoploss,
            "tp": takeprofit,
            "comment": comment,
            "magic": magic,
            "open_time": datetime.now(),
            "status": "open",
        }
        self._last_error = ERR_NO_ERROR
        return ticket

    def close_order(
        self, ticket: int, volume: float, close_price: float, slippage: int
    ) -> bool:
        """Close an open order and return whether the operation succeeded."""

        if random.random() < self.error_rate:
            self._last_error = random.choice(
                [
                    ERR_COMMON_ERROR,
                    ERR_SERVER_BUSY,
                    ERR_PRICE_CHANGED,
                    ERR_MALFUNCTIONAL_TRADE,
                ]
            )
            return False

        if (
            ticket not in self._open_orders
            or self._open_orders[ticket]["status"] != "open"
        ):
            self._last_error = ERR_INVALID_TICKET
            return False

        order = self._open_orders[ticket]
        market_info = self.get_market_info(order["symbol"])
        digits = market_info.get("MODE_DIGITS", 5)
        point = market_info.get("MODE_POINT", 0.00001)

        actual_close_price = close_price
        if order["cmd"] in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]:
            if actual_close_price > market_info["bid"] + slippage * point:
                self._last_error = ERR_PRICE_CHANGED
                return False
            actual_close_price = _normalize_double(
                min(actual_close_price, market_info["bid"] + slippage * point), digits
            )
        elif order["cmd"] in [OP_SELL, OP_SELLLIMIT, OP_SELLSTOP]:
            if actual_close_price < market_info["ask"] - slippage * point:
                self._last_error = ERR_PRICE_CHANGED
                return False
            actual_close_price = _normalize_double(
                max(actual_close_price, market_info["ask"] - slippage * point), digits
            )

        order["close_price"] = actual_close_price
        order["close_time"] = datetime.now()
        order["status"] = "closed"
        self._last_error = ERR_NO_ERROR
        return True

    def get_last_error(self) -> int:
        """Get the last error code."""

        return getattr(self, "_last_error", ERR_NO_ERROR)


class MockBrokerClient:
    """BrokerClient adapter that hides the legacy mock broker implementation."""

    def __init__(self, broker_api: MockBrokerAPI | None = None) -> None:
        from app.services.order_management import OrderManager

        self.broker_api = broker_api or MockBrokerAPI(trade_allowed=True)
        self.order_manager = OrderManager(self.broker_api)

    def place_order(self, order: OrderCreate) -> BrokerOrder:
        """Place an order through the mock broker."""

        ticket = self.order_manager.send_order_reliable(
            symbol=order.symbol.upper(),
            cmd=_ORDER_TYPE_TO_CMD[order.order_type],
            volume=order.volume,
            price=order.price,
            slippage=order.slippage,
            stoploss=order.stop_loss,
            takeprofit=order.take_profit,
            comment=order.comment,
            magic=order.magic,
        )
        if ticket == -1:
            return {"ticket": -1, "status": "rejected"}
        return self.broker_api._open_orders[ticket]

    def close_order(self, ticket: int, order_close: OrderClose) -> BrokerOrder:
        """Close an order through the mock broker."""

        broker_order = self.get_order(ticket)
        if broker_order is None:
            self.broker_api._last_error = ERR_INVALID_TICKET
            return {"ticket": ticket, "status": "not_found"}

        success = self.order_manager.close_order_reliable(
            ticket=ticket,
            volume=order_close.volume or broker_order["volume"],
            close_price=order_close.price,
            slippage=order_close.slippage,
            order_details=broker_order,
            exit_reason=order_close.exit_reason,
        )
        if not success:
            return broker_order
        return self.broker_api._open_orders[ticket]

    def get_open_orders(self) -> list[BrokerOrder]:
        """Return all open orders known to the mock broker."""

        return [
            order
            for order in self.broker_api._open_orders.values()
            if order["status"] == "open"
        ]

    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        """Return a lightweight mock account snapshot."""

        open_orders = self.get_open_orders()
        return {
            "provider": "mock",
            "trade_allowed": self.broker_api.is_trade_allowed(),
            "open_orders": len(open_orders),
            "known_orders": len(self.broker_api._open_orders),
            "last_error": self.get_last_error(),
        }

    def get_order(self, ticket: int) -> BrokerOrder | None:
        """Return a broker order by ticket, including closed orders."""

        return self.broker_api._open_orders.get(ticket)

    def get_last_error(self) -> int:
        """Return the last error reported by the mock order manager."""

        manager_error = self.order_manager.get_last_error()
        if manager_error != ERR_NO_ERROR:
            return manager_error
        return self.broker_api.get_last_error()


class MockBroker:
    """Deterministic in-memory broker facade kept for compatibility tests."""

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


__all__ = ["MockBroker", "MockBrokerAPI", "MockBrokerClient"]
