"""Broker simulation and order management module.

Implements MockBrokerAPI and OrderManager classes for reliable order execution.
Replicates MQL4-like behavior with proper error handling and slippage simulation.
"""

from typing import Optional, Callable, Dict, Any
from datetime import datetime
import random
import time
import logging

logger = logging.getLogger(__name__)

# --- MQL4-like Order Types ---
OP_BUY = 0
OP_SELL = 1
OP_BUYSTOP = 2
OP_SELLSTOP = 3
OP_BUYLIMIT = 4
OP_SELLLIMIT = 5

# --- MQL4-like Error Codes ---
ERR_NO_ERROR = 0
ERR_COMMON_ERROR = 1
ERR_NO_CONNECTION = 2
ERR_INVALID_TRADE_PARAMETERS = 3
ERR_SERVER_BUSY = 4
ERR_OLD_VERSION = 5
ERR_NO_CHANGES = 6
ERR_TRADE_CONTEXT_BUSY = 129
ERR_PRICE_CHANGED = 130
ERR_OFF_QUOTES = 131
ERR_INVALID_STOPS = 132
ERR_TRADE_DISABLED = 133
ERR_NOT_ENOUGH_MONEY = 134
ERR_MARKET_CLOSED = 135
ERR_LOCK_TIMEOUT = 136
ERR_ORDER_EXPIRED = 137
ERR_REQUOTE = 138
ERR_BROKER_BUSY = 139
ERR_INVALID_TICKET = 140
ERR_MALFUNCTIONAL_TRADE = 141
ERR_TOO_MANY_REQUESTS = 142
ERR_INVALID_PRICE = 146
ERR_CLOSE_TIMEOUT = 147


# --- Custom Exception Classes ---
class OrderError(Exception):
    """Base exception for order-related errors."""
    pass


class BrokerConnectionError(OrderError):
    """Exception for broker connection issues."""
    pass


class TradeContextBusyError(OrderError):
    """Exception when the trade context is busy."""
    pass


class InvalidPriceError(OrderError):
    """Exception for invalid or changed prices."""
    pass


class InvalidStopLossError(OrderError):
    """Exception when stop loss/take profit levels are too close to market."""
    pass


class TradeRejectedError(OrderError):
    """Exception for general trade rejections by the broker/server."""
    pass


class MalfunctionalTradeError(OrderError):
    """Exception for malfunctional trade operations."""
    pass


# Map error codes to custom exception classes
ERROR_MAP = {
    ERR_NO_CONNECTION: BrokerConnectionError,
    ERR_TRADE_CONTEXT_BUSY: TradeContextBusyError,
    ERR_INVALID_PRICE: InvalidPriceError,
    ERR_OFF_QUOTES: InvalidPriceError,
    ERR_REQUOTE: InvalidPriceError,
    ERR_PRICE_CHANGED: InvalidPriceError,
    ERR_INVALID_STOPS: InvalidStopLossError,
    ERR_BROKER_BUSY: TradeContextBusyError,
    ERR_MALFUNCTIONAL_TRADE: MalfunctionalTradeError,
    ERR_INVALID_TICKET: TradeRejectedError,
    ERR_ORDER_EXPIRED: TradeRejectedError,
    ERR_CLOSE_TIMEOUT: TradeRejectedError
}


def _normalize_double(value: float, digits: int) -> float:
    """Normalize float to specified decimal places (MQL4 NormalizeDouble)."""
    return round(value, digits)


def exponential_backoff_sleep(mean_time: float, max_time: float):
    """Sleep with exponential backoff and jitter."""
    if mean_time <= 0:
        return
    base_sleep = random.uniform(0.5, 1.5) * mean_time
    sleep_duration = min(base_sleep, max_time)
    time.sleep(sleep_duration)


def ensure_valid_stop_level(
    symbol: str, price: float, stop_level: float, is_buy_order: bool, market_info: dict
) -> float:
    """Ensure stop loss/take profit respects broker minimum distance (MQL4 OrderReliable_EnsureValidStop)."""
    if stop_level == 0:
        return 0.0
    
    mode_stoplevel = market_info.get('MODE_STOPLEVEL', 20)
    mode_point = market_info.get('MODE_POINT', 0.00001)
    digits = market_info.get('MODE_DIGITS', 5)
    
    servers_min_stop = mode_stoplevel * mode_point
    
    if servers_min_stop <= 0:
        return stop_level
    
    if abs(price - stop_level) < servers_min_stop:
        if is_buy_order:
            stop_level = price - servers_min_stop
        else:
            stop_level = price + servers_min_stop
        stop_level = _normalize_double(stop_level, digits)
    
    return stop_level


class MockBrokerAPI:
    """Simulates a broker API with order management and market data."""

    def __init__(self, error_rate: float = 0.0):
        """Initialize mock broker.
        
        Args:
            error_rate: Probability of random order rejection (0.0-1.0).
        """
        self._trade_allowed = False
        self._open_orders: Dict[int, Dict[str, Any]] = {}
        self._next_ticket = 100000
        self._market_data = {
            "EURUSD": {
                "bid": 1.08500, "ask": 1.08510,
                "MODE_POINT": 0.00001, "MODE_STOPLEVEL": 20, "MODE_DIGITS": 5
            },
            "TSLA": {
                "bid": 200.00, "ask": 200.10,
                "MODE_POINT": 0.01, "MODE_STOPLEVEL": 1, "MODE_DIGITS": 2
            }
        }
        self.error_rate = error_rate
        self._last_error = ERR_NO_ERROR

    def get_market_info(self, symbol: str) -> dict:
        """Get market info for symbol."""
        self.refresh_rates(symbol)
        return self._market_data.get(
            symbol,
            {"bid": 0.0, "ask": 0.0, "MODE_POINT": 0.00001, "MODE_STOPLEVEL": 20, "MODE_DIGITS": 5}
        )

    def is_trade_allowed(self) -> bool:
        """Check if trading is allowed."""
        return self._trade_allowed

    def refresh_rates(self, symbol: str):
        """Simulate price fluctuations."""
        if symbol in self._market_data:
            data = self._market_data[symbol]
            digits = data.get('MODE_DIGITS', 5)
            fluctuation = random.uniform(-0.0001, 0.0001) if digits == 5 else random.uniform(-0.01, 0.01)
            data["bid"] = _normalize_double(data["bid"] + fluctuation, digits)
            data["ask"] = _normalize_double(data["ask"] + fluctuation, digits)
            if data["ask"] <= data["bid"]:
                data["ask"] = _normalize_double(data["bid"] + data["MODE_POINT"], digits)

    def send_order(
        self,
        symbol: str, cmd: int, volume: float, price: float, slippage: int,
        stoploss: float, takeprofit: float, comment: str, magic: int
    ) -> int:
        """Send an order to the broker.
        
        Returns:
            Ticket number if successful, -1 if failed.
        """
        if not self._trade_allowed:
            self._last_error = ERR_TRADE_DISABLED
            return -1
        
        if random.random() < self.error_rate:
            self._last_error = random.choice([
                ERR_COMMON_ERROR, ERR_SERVER_BUSY, ERR_PRICE_CHANGED, ERR_INVALID_TRADE_PARAMETERS
            ])
            return -1
        
        market_info = self.get_market_info(symbol)
        digits = market_info.get('MODE_DIGITS', 5)
        point = market_info.get('MODE_POINT', 0.00001)
        
        actual_price = price
        if cmd in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]:
            if actual_price < market_info["ask"] - slippage * point:
                self._last_error = ERR_REQUOTE
                return -1
            actual_price = _normalize_double(max(actual_price, market_info["ask"] - slippage * point), digits)
        elif cmd in [OP_SELL, OP_SELLLIMIT, OP_SELLSTOP]:
            if actual_price > market_info["bid"] + slippage * point:
                self._last_error = ERR_REQUOTE
                return -1
            actual_price = _normalize_double(min(actual_price, market_info["bid"] + slippage * point), digits)
        
        is_buy = cmd in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]
        stoploss = ensure_valid_stop_level(symbol, actual_price, stoploss, is_buy, market_info)
        takeprofit = ensure_valid_stop_level(symbol, actual_price, takeprofit, is_buy, market_info)
        
        if (stoploss != 0 and is_buy and stoploss >= actual_price) or \
           (stoploss != 0 and not is_buy and stoploss <= actual_price):
            self._last_error = ERR_INVALID_STOPS
            return -1
        if (takeprofit != 0 and is_buy and takeprofit <= actual_price) or \
           (takeprofit != 0 and not is_buy and takeprofit >= actual_price):
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
            "status": "open"
        }
        self._last_error = ERR_NO_ERROR
        return ticket

    def close_order(self, ticket: int, volume: float, close_price: float, slippage: int) -> bool:
        """Close an open order.
        
        Returns:
            True if successful, False otherwise.
        """
        if random.random() < self.error_rate:
            self._last_error = random.choice([
                ERR_COMMON_ERROR, ERR_SERVER_BUSY, ERR_PRICE_CHANGED, ERR_MALFUNCTIONAL_TRADE
            ])
            return False
        
        if ticket not in self._open_orders or self._open_orders[ticket]["status"] != "open":
            self._last_error = ERR_INVALID_TICKET
            return False
        
        order = self._open_orders[ticket]
        market_info = self.get_market_info(order["symbol"])
        digits = market_info.get('MODE_DIGITS', 5)
        point = market_info.get('MODE_POINT', 0.00001)
        
        actual_close_price = close_price
        if order["cmd"] in [OP_BUY, OP_BUYLIMIT, OP_BUYSTOP]:
            if actual_close_price > market_info["bid"] + slippage * point:
                self._last_error = ERR_PRICE_CHANGED
                return False
            actual_close_price = _normalize_double(min(actual_close_price, market_info["bid"] + slippage * point), digits)
        elif order["cmd"] in [OP_SELL, OP_SELLLIMIT, OP_SELLSTOP]:
            if actual_close_price < market_info["ask"] - slippage * point:
                self._last_error = ERR_PRICE_CHANGED
                return False
            actual_close_price = _normalize_double(max(actual_close_price, market_info["ask"] - slippage * point), digits)
        
        order["close_price"] = actual_close_price
        order["close_time"] = datetime.now()
        order["status"] = "closed"
        self._last_error = ERR_NO_ERROR
        return True

    def get_last_error(self) -> int:
        """Get the last error code."""
        return getattr(self, '_last_error', ERR_NO_ERROR)


class OrderManager:
    """Reliable order execution with retries and error handling."""

    def __init__(
        self,
        broker_api: MockBrokerAPI,
        retry_attempts: int = 5,
        sleep_time: float = 0.1,
        sleep_maximum: float = 1.0,
        max_close_duration: float = 10.0,
        on_order_closed: Optional[Callable] = None,
    ):
        """Initialize order manager.
        
        Args:
            broker_api: MockBrokerAPI instance.
            retry_attempts: Max retries for order operations.
            sleep_time: Base sleep time between retries (seconds).
            sleep_maximum: Maximum sleep time (seconds).
            max_close_duration: Maximum time to spend closing an order (seconds).
            on_order_closed: Callback function when order closes.
        """
        self.broker_api = broker_api
        self.retry_attempts = retry_attempts
        self.sleep_time = sleep_time
        self.sleep_maximum = sleep_maximum
        self.max_close_duration = max_close_duration
        self.on_order_closed = on_order_closed
        self._last_error = ERR_NO_ERROR

    def _handle_error(self, error_code: int, message: str):
        """Handle error and raise appropriate exception."""
        self._last_error = error_code
        exception_class = ERROR_MAP.get(error_code, OrderError)
        raise exception_class(f"Error {error_code}: {message}")

    def send_order_reliable(
        self,
        symbol: str, cmd: int, volume: float, price: float, slippage: int,
        stoploss: float, takeprofit: float, comment: str, magic: int
    ) -> int:
        """Send order with retries and error handling.
        
        Returns:
            Ticket number if successful, -1 if failed.
        """
        for attempt in range(self.retry_attempts):
            try:
                ticket = self.broker_api.send_order(
                    symbol, cmd, volume, price, slippage, stoploss, takeprofit, comment, magic
                )
                if ticket != -1:
                    return ticket
                
                error_code = self.broker_api.get_last_error()
                if error_code in [ERR_TRADE_CONTEXT_BUSY, ERR_SERVER_BUSY, ERR_BROKER_BUSY]:
                    exponential_backoff_sleep(self.sleep_time * (2 ** attempt), self.sleep_maximum)
                    continue
                elif error_code in [ERR_PRICE_CHANGED, ERR_REQUOTE]:
                    market_info = self.broker_api.get_market_info(symbol)
                    if cmd in [OP_BUY, OP_BUYSTOP, OP_BUYLIMIT]:
                        price = market_info['ask']
                    elif cmd in [OP_SELL, OP_SELLSTOP, OP_SELLLIMIT]:
                        price = market_info['bid']
                    continue
                else:
                    self._handle_error(error_code, f"Failed to send order after {attempt+1} attempts.")
            
            except OrderError as e:
                self._last_error = self.broker_api.get_last_error()
                logger.error(f"Order error: {e}")
                if isinstance(e, (TradeContextBusyError, InvalidPriceError)) and attempt < self.retry_attempts - 1:
                    exponential_backoff_sleep(self.sleep_time * (2 ** attempt), self.sleep_maximum)
                    continue
                return -1
            except Exception as e:
                self._last_error = ERR_COMMON_ERROR
                logger.error(f"Unexpected error: {e}")
                return -1
        
        self._last_error = ERR_COMMON_ERROR
        return -1

    def close_order_reliable(
        self,
        ticket: int, volume: float, close_price: float, slippage: int,
        pnl: float = 0.0, order_details: Optional[dict] = None, exit_reason: str = ""
    ) -> bool:
        """Close order with retries and error handling.
        
        Returns:
            True if successful, False otherwise.
        """
        start_time = time.time()
        while time.time() - start_time < self.max_close_duration:
            try:
                success = self.broker_api.close_order(ticket, volume, close_price, slippage)
                if success:
                    if self.on_order_closed:
                        self.on_order_closed(ticket, True, close_price, pnl, order_details, exit_reason)
                    return True
                
                error_code = self.broker_api.get_last_error()
                if error_code in [ERR_TRADE_CONTEXT_BUSY, ERR_SERVER_BUSY, ERR_BROKER_BUSY, ERR_CLOSE_TIMEOUT]:
                    exponential_backoff_sleep(self.sleep_time, self.sleep_maximum)
                    continue
                elif error_code == ERR_PRICE_CHANGED:
                    order = self.broker_api._open_orders.get(ticket)
                    if order:
                        market_info = self.broker_api.get_market_info(order["symbol"])
                        close_price = market_info['bid'] if order["cmd"] == OP_BUY else market_info['ask']
                    continue
                else:
                    self._handle_error(error_code, f"Failed to close order {ticket}.")
            
            except OrderError as e:
                logger.error(f"Order error during close: {e}")
                if self.on_order_closed:
                    self.on_order_closed(ticket, False, close_price, pnl, order_details, exit_reason)
                return False
            except Exception as e:
                logger.error(f"Unexpected error during close: {e}")
                if self.on_order_closed:
                    self.on_order_closed(ticket, False, close_price, pnl, order_details, exit_reason)
                return False
        
        self._last_error = ERR_CLOSE_TIMEOUT
        if self.on_order_closed:
            self.on_order_closed(ticket, False, close_price, pnl, order_details, exit_reason)
        return False

    def get_last_error(self) -> int:
        """Get last error code."""
        return self._last_error
