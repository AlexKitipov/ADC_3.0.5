"""Broker simulation and order management module.

Re-exports :class:`MockBrokerAPI` and implements :class:`OrderManager`
for reliable order execution. The module mirrors MQL4-style order operations with explicit error
codes, broker stop-level validation, slippage simulation, and retry handling.
"""

import logging
import time
from typing import Any, Callable, Optional

from app.services.broker.mql4 import (
    ERROR_MAP,
    ERR_BROKER_BUSY,
    ERR_CLOSE_TIMEOUT,
    ERR_COMMON_ERROR,
    ERR_INVALID_PRICE,
    ERR_INVALID_STOPS,
    ERR_INVALID_TICKET,
    ERR_INVALID_TRADE_PARAMETERS,
    ERR_LOCK_TIMEOUT,
    ERR_MALFUNCTIONAL_TRADE,
    ERR_MARKET_CLOSED,
    ERR_NO_CHANGES,
    ERR_NO_CONNECTION,
    ERR_NO_ERROR,
    ERR_NOT_ENOUGH_MONEY,
    ERR_OFF_QUOTES,
    ERR_OLD_VERSION,
    ERR_ORDER_EXPIRED,
    ERR_PRICE_CHANGED,
    ERR_REQUOTE,
    ERR_SERVER_BUSY,
    ERR_TOO_MANY_REQUESTS,
    ERR_TRADE_CONTEXT_BUSY,
    ERR_TRADE_DISABLED,
    BrokerConnectionError,
    InvalidPriceError,
    InvalidStopLossError,
    MalfunctionalTradeError,
    OP_BUY,
    OP_BUYLIMIT,
    OP_BUYSTOP,
    OP_SELL,
    OP_SELLLIMIT,
    OP_SELLSTOP,
    OrderError,
    TradeContextBusyError,
    TradeRejectedError,
    _normalize_double,
    ensure_valid_stop_level,
    exponential_backoff_sleep,
)

from app.services.broker.mock_broker import MockBrokerAPI


class OrderManager:
    """Reliable order execution with retries and error handling."""

    def __init__(
        self,
        broker_api: MockBrokerAPI,
        retry_attempts: int = 5,
        sleep_time: float = 0.1,
        sleep_maximum: float = 1.0,
        max_close_duration: float = 10.0,
        on_order_closed: Optional[Callable[..., None]] = None,
    ) -> None:
        """Initialize the order manager."""

        self.broker_api = broker_api
        self.retry_attempts = retry_attempts
        self.sleep_time = sleep_time
        self.sleep_maximum = sleep_maximum
        self.max_close_duration = max_close_duration
        self.on_order_closed = on_order_closed
        self._last_error = ERR_NO_ERROR

    def _handle_error(self, error_code: int, message: str) -> None:
        """Handle an error and raise the appropriate exception."""

        self._last_error = error_code
        exception_class = ERROR_MAP.get(error_code, OrderError)
        raise exception_class(f"Error {error_code}: {message}")

    def send_order_reliable(
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
        """Send an order with retries and error handling."""

        for attempt in range(self.retry_attempts):
            try:
                ticket = self.broker_api.send_order(
                    symbol,
                    cmd,
                    volume,
                    price,
                    slippage,
                    stoploss,
                    takeprofit,
                    comment,
                    magic,
                )
                if ticket != -1:
                    self._last_error = ERR_NO_ERROR
                    return ticket

                error_code = self.broker_api.get_last_error()
                if error_code in [
                    ERR_TRADE_CONTEXT_BUSY,
                    ERR_SERVER_BUSY,
                    ERR_TOO_MANY_REQUESTS,
                    ERR_BROKER_BUSY,
                ]:
                    exponential_backoff_sleep(
                        self.sleep_time * (2**attempt), self.sleep_maximum
                    )
                    continue
                if error_code in [ERR_PRICE_CHANGED, ERR_REQUOTE]:
                    market_info = self.broker_api.get_market_info(symbol)
                    if cmd in [OP_BUY, OP_BUYSTOP, OP_BUYLIMIT]:
                        price = market_info["ask"]
                    elif cmd in [OP_SELL, OP_SELLSTOP, OP_SELLLIMIT]:
                        price = market_info["bid"]
                    continue

                self._handle_error(
                    error_code, f"Failed to send order after {attempt + 1} attempts."
                )

            except OrderError as exc:
                self._last_error = self.broker_api.get_last_error()
                logger.error("Order error: %s", exc)
                if (
                    isinstance(exc, (TradeContextBusyError, InvalidPriceError))
                    and attempt < self.retry_attempts - 1
                ):
                    exponential_backoff_sleep(
                        self.sleep_time * (2**attempt), self.sleep_maximum
                    )
                    continue
                return -1
            except Exception as exc:  # pragma: no cover - defensive safety net
                self._last_error = ERR_COMMON_ERROR
                logger.error("Unexpected error: %s", exc)
                return -1

        self._last_error = ERR_COMMON_ERROR
        return -1

    def close_order_reliable(
        self,
        ticket: int,
        volume: float,
        close_price: float,
        slippage: int,
        pnl: float = 0.0,
        order_details: Optional[dict[str, Any]] = None,
        exit_reason: str = "",
    ) -> bool:
        """Close an order with retries and error handling."""

        start_time = time.time()
        while time.time() - start_time < self.max_close_duration:
            try:
                success = self.broker_api.close_order(
                    ticket, volume, close_price, slippage
                )
                if success:
                    self._last_error = ERR_NO_ERROR
                    if self.on_order_closed:
                        self.on_order_closed(
                            ticket, True, close_price, pnl, order_details, exit_reason
                        )
                    return True

                error_code = self.broker_api.get_last_error()
                if error_code in [
                    ERR_TRADE_CONTEXT_BUSY,
                    ERR_SERVER_BUSY,
                    ERR_TOO_MANY_REQUESTS,
                    ERR_BROKER_BUSY,
                    ERR_CLOSE_TIMEOUT,
                ]:
                    exponential_backoff_sleep(self.sleep_time, self.sleep_maximum)
                    continue
                if error_code == ERR_PRICE_CHANGED:
                    order = self.broker_api._open_orders.get(ticket)
                    if order:
                        market_info = self.broker_api.get_market_info(order["symbol"])
                        close_price = (
                            market_info["bid"]
                            if order["cmd"] in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]
                            else market_info["ask"]
                        )
                    continue

                self._handle_error(error_code, f"Failed to close order {ticket}.")

            except OrderError as exc:
                self._last_error = self.broker_api.get_last_error()
                logger.error("Order error during close: %s", exc)
                if self.on_order_closed:
                    self.on_order_closed(
                        ticket, False, close_price, pnl, order_details, exit_reason
                    )
                return False
            except Exception as exc:  # pragma: no cover - defensive safety net
                self._last_error = ERR_COMMON_ERROR
                logger.error("Unexpected error during close: %s", exc)
                if self.on_order_closed:
                    self.on_order_closed(
                        ticket, False, close_price, pnl, order_details, exit_reason
                    )
                return False

        self._last_error = ERR_CLOSE_TIMEOUT
        if self.on_order_closed:
            self.on_order_closed(
                ticket, False, close_price, pnl, order_details, exit_reason
            )
        return False

    def get_last_error(self) -> int:
        """Get the last error code."""

        return self._last_error
