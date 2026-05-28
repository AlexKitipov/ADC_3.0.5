"""Mock market-data streaming services for live strategy simulations.

The original notebook/README drives manual trading through a redirected mock
WebSocket client that emits synthetic ticks, writes them to an output widget,
and invokes a strategy callback.  This backend module keeps the same role while
removing notebook-only dependencies: consumers can subscribe with a normal
Python callback, optionally mirror messages to any object with
``append_stdout()``, and use the supplied broker simulation as the market-info
source of truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import random
import threading
import time
from typing import Any, Callable, Optional, Protocol

from app.services.order_management import MockBrokerAPI


MarketDataCallback = Callable[[dict[str, Any]], None]


class OutputSink(Protocol):
    """Protocol for notebook-like output objects used by the legacy workflow."""

    def append_stdout(self, text: str) -> None:
        """Append a line of text to the output sink."""


@dataclass(frozen=True)
class MarketTick:
    """Single synthetic market-data tick emitted by the mock stream."""

    symbol: str
    price: float
    bid: float
    ask: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary payload compatible with the notebook callbacks."""

        return asdict(self)


class MockWebSocketClient:
    """Threaded synthetic WebSocket client for strategy and order-manager tests.

    The client mirrors the README ``RedirectedMockWebSocketClient`` behavior:
    it perturbs the current price on a fixed interval, normalizes the price to
    the broker's configured digits, writes a human-readable stream message when
    an output sink is provided, and sends each payload to ``on_data_received``.
    """

    def __init__(
        self,
        broker_api: MockBrokerAPI,
        symbol: str = "EURUSD",
        initial_price: float = 1.20000,
        price_volatility: float = 0.0001,
        stream_interval: float = 1.0,
        on_data_received: Optional[MarketDataCallback] = None,
        output_sink: Optional[OutputSink] = None,
        random_seed: Optional[int] = None,
    ) -> None:
        """Initialize the synthetic stream.

        Args:
            broker_api: Broker simulation used for symbol precision and spread.
            symbol: Symbol to stream.
            initial_price: Starting mid price before the first synthetic tick.
            price_volatility: Maximum absolute random-walk width per tick.
            stream_interval: Delay in seconds between ticks.
            on_data_received: Optional callback receiving each tick dictionary.
            output_sink: Optional object with ``append_stdout`` for stream logs.
            random_seed: Optional deterministic seed for reproducible tests.
        """

        if stream_interval < 0:
            raise ValueError("stream_interval must be non-negative")
        if price_volatility < 0:
            raise ValueError("price_volatility must be non-negative")

        self.broker_api = broker_api
        self.symbol = symbol
        self.price_volatility = price_volatility
        self.stream_interval = stream_interval
        self.on_data_received = on_data_received
        self.output_sink = output_sink
        self._current_price = initial_price
        self._streaming = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._rng = random.Random(random_seed)
        self.last_tick: Optional[MarketTick] = None

    @property
    def is_streaming(self) -> bool:
        """Return whether the background stream is currently running."""

        return self._streaming

    @property
    def current_price(self) -> float:
        """Return the latest generated mid price in a thread-safe way."""

        with self._lock:
            return self._current_price

    def connect(self) -> None:
        """Start the background price stream if it is not already running."""

        if self._streaming:
            return

        self._streaming = True
        self._thread = threading.Thread(
            target=self._simulate_price_stream,
            name=f"mock-ws-{self.symbol}",
            daemon=True,
        )
        self._thread.start()
        self._write_output(f"WebSocket stream STARTED for {self.symbol}.\n")

    def disconnect(self) -> None:
        """Stop the background stream and wait briefly for it to exit."""

        if not self._streaming:
            return

        self._streaming = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(self.stream_interval * 2, 0.1))
        self._write_output(f"WebSocket stream STOPPED for {self.symbol}.\n")

    def generate_tick(self) -> MarketTick:
        """Generate one synthetic tick without requiring the background thread."""

        with self._lock:
            market_info = self.broker_api.get_market_info(self.symbol)
            digits = int(market_info.get("MODE_DIGITS", 5))
            point = float(market_info.get("MODE_POINT", 0.00001))
            raw_spread = float(market_info.get("ask", 0)) - float(
                market_info.get("bid", 0)
            )
            spread = max(raw_spread, point)
            change = (self._rng.random() - 0.5) * self.price_volatility
            self._current_price = round(self._current_price + change, digits)
            bid = round(self._current_price - spread / 2, digits)
            ask = round(self._current_price + spread / 2, digits)
            tick = MarketTick(
                symbol=self.symbol,
                price=self._current_price,
                bid=bid,
                ask=ask,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.last_tick = tick
            return tick

    def _simulate_price_stream(self) -> None:
        while self._streaming:
            tick = self.generate_tick()
            payload = tick.to_dict()
            self._write_output(
                f"WS Stream: {payload['symbol']} Price: {payload['price']}\n"
            )
            if self.on_data_received:
                self.on_data_received(payload)
            if self.stream_interval > 0:
                time.sleep(self.stream_interval)

    def _write_output(self, text: str) -> None:
        if self.output_sink:
            self.output_sink.append_stdout(text)

    def __enter__(self) -> "MockWebSocketClient":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.disconnect()


class RedirectedMockWebSocketClient(MockWebSocketClient):
    """Backward-compatible alias using the README constructor naming."""

    def __init__(
        self,
        output_widget: Optional[OutputSink],
        broker_api: MockBrokerAPI,
        symbol: str = "EURUSD",
        initial_price: float = 1.20000,
        price_volatility: float = 0.0001,
        stream_interval: float = 1.0,
        on_data_received: Optional[MarketDataCallback] = None,
        random_seed: Optional[int] = None,
    ) -> None:
        super().__init__(
            broker_api=broker_api,
            symbol=symbol,
            initial_price=initial_price,
            price_volatility=price_volatility,
            stream_interval=stream_interval,
            on_data_received=on_data_received,
            output_sink=output_widget,
            random_seed=random_seed,
        )


def get_default_dates(now: Optional[datetime] = None) -> tuple[str, str]:
    """Return the default two-year date window used by the simulation UI."""

    current = now or datetime.now(timezone.utc)
    end_date = current.strftime("%Y-%m-%d")
    start_date = (current - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    return start_date, end_date
