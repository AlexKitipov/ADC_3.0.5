"""MQL4-style broker constants, errors, and validation helpers."""

from __future__ import annotations

import random
import time
from typing import Any

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


class OrderError(Exception):
    """Base exception for order-related errors."""


class BrokerConnectionError(OrderError):
    """Exception for broker connection issues."""


class TradeContextBusyError(OrderError):
    """Exception when the trade context is busy."""


class InvalidPriceError(OrderError):
    """Exception for invalid or changed prices."""


class InvalidStopLossError(OrderError):
    """Exception when stop loss/take profit levels are too close to market."""


class TradeRejectedError(OrderError):
    """Exception for general trade rejections by the broker/server."""


class MalfunctionalTradeError(OrderError):
    """Exception for malfunctional trade operations."""


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
    ERR_CLOSE_TIMEOUT: TradeRejectedError,
}


def _normalize_double(value: float, digits: int) -> float:
    """Normalize a float to the requested decimal precision."""

    return round(value, digits)


def exponential_backoff_sleep(mean_time: float, max_time: float) -> None:
    """Sleep with exponential backoff and jitter."""

    if mean_time <= 0:
        return

    base_sleep = random.uniform(0.5, 1.5) * mean_time
    sleep_duration = min(base_sleep, max_time)
    time.sleep(sleep_duration)


def ensure_valid_stop_level(
    symbol: str,
    price: float,
    stop_level: float,
    is_buy_order: bool,
    market_info: dict[str, Any],
) -> float:
    """Ensure a stop level respects the broker's minimum distance."""

    del symbol
    if stop_level == 0:
        return 0.0

    mode_stoplevel = market_info.get("MODE_STOPLEVEL", 20)
    mode_point = market_info.get("MODE_POINT", 0.00001)
    digits = market_info.get("MODE_DIGITS", 5)
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


__all__ = [
    "BrokerConnectionError",
    "ERROR_MAP",
    "ERR_BROKER_BUSY",
    "ERR_CLOSE_TIMEOUT",
    "ERR_COMMON_ERROR",
    "ERR_INVALID_PRICE",
    "ERR_INVALID_STOPS",
    "ERR_INVALID_TICKET",
    "ERR_INVALID_TRADE_PARAMETERS",
    "ERR_LOCK_TIMEOUT",
    "ERR_MALFUNCTIONAL_TRADE",
    "ERR_MARKET_CLOSED",
    "ERR_NO_CHANGES",
    "ERR_NO_CONNECTION",
    "ERR_NO_ERROR",
    "ERR_NOT_ENOUGH_MONEY",
    "ERR_OFF_QUOTES",
    "ERR_OLD_VERSION",
    "ERR_ORDER_EXPIRED",
    "ERR_PRICE_CHANGED",
    "ERR_REQUOTE",
    "ERR_SERVER_BUSY",
    "ERR_TOO_MANY_REQUESTS",
    "ERR_TRADE_CONTEXT_BUSY",
    "ERR_TRADE_DISABLED",
    "InvalidPriceError",
    "InvalidStopLossError",
    "MalfunctionalTradeError",
    "OP_BUY",
    "OP_BUYLIMIT",
    "OP_BUYSTOP",
    "OP_SELL",
    "OP_SELLLIMIT",
    "OP_SELLSTOP",
    "OrderError",
    "TradeContextBusyError",
    "TradeRejectedError",
    "_normalize_double",
    "ensure_valid_stop_level",
    "exponential_backoff_sleep",
]
