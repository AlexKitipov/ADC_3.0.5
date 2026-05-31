"""Deterministic facade for signal decision generation.

This module intentionally does not replace the legacy signal endpoint logic yet.
It provides a stable bounded-context seam that later PRs can wire into routers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

import pandas as pd

from app.services.data.providers import MarketDataProvider
from core.indicators import TechnicalIndicators


DEFAULT_TIMEFRAME = "1d"
DEFAULT_RSI_LOWER = 30.0
DEFAULT_RSI_UPPER = 70.0
DEFAULT_RSI_PERIOD = 14
DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9
DEFAULT_ATR_PERIOD = 14


@dataclass(frozen=True, init=False)
class SignalDecision:
    """Serializable trading-signal decision DTO.

    The DTO stays dataclass-first while exposing ``model_dump``/``dict`` helpers
    compatible with the subset of Pydantic serialization commonly used by the
    application and tests. ``rationale`` is accepted as a backwards-compatible
    alias for the new ``explanation`` field.
    """

    symbol: str
    action: str
    confidence: float
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        symbol: str,
        action: str,
        confidence: float,
        explanation: str | None = None,
        metadata: dict[str, Any] | None = None,
        rationale: str | None = None,
    ) -> None:
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "confidence", _clamp(confidence))
        object.__setattr__(self, "explanation", explanation or rationale or "")
        object.__setattr__(self, "metadata", dict(metadata or {}))

    @property
    def rationale(self) -> str:
        """Backward-compatible explanation alias."""

        return self.explanation

    def model_dump(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the decision."""

        return asdict(self)

    def dict(self) -> dict[str, Any]:
        """Pydantic v1-style serialization alias."""

        return self.model_dump()


def generate_signal(
    symbol: str | None,
    timeframe: str | None,
    strategy_settings: Mapping[str, Any] | None,
    data_provider: MarketDataProvider,
) -> SignalDecision:
    """Generate a deterministic BUY/SELL/HOLD decision from OHLCV indicators.

    The production request path deliberately stays free from TensorFlow, RL, and
    other non-deterministic model dependencies. The ruleset is intentionally
    compact and explainable:

    * BUY when RSI is oversold and MACD line/histogram are improving.
    * SELL when RSI is overbought and MACD line/histogram are weakening.
    * HOLD for neutral, incomplete, or invalid market data.
    """

    normalized_symbol = (symbol or "UNKNOWN").upper()
    normalized_timeframe = timeframe or DEFAULT_TIMEFRAME
    settings = dict(strategy_settings or {})

    rsi_lower = _setting_float(settings, "rsi_lower", DEFAULT_RSI_LOWER)
    rsi_upper = _setting_float(settings, "rsi_upper", DEFAULT_RSI_UPPER)
    rsi_period = _setting_int(settings, "rsi_period", DEFAULT_RSI_PERIOD)
    macd_fast = _setting_int(settings, "macd_fast", DEFAULT_MACD_FAST)
    macd_slow = _setting_int(settings, "macd_slow", DEFAULT_MACD_SLOW)
    macd_signal = _setting_int(settings, "macd_signal", DEFAULT_MACD_SIGNAL)
    atr_period = _setting_int(settings, "atr_period", DEFAULT_ATR_PERIOD)
    min_bars = max(rsi_period + 1, macd_slow + macd_signal, atr_period + 1)

    try:
        raw_data = data_provider.get_ohlcv(normalized_symbol, normalized_timeframe)
    except Exception as exc:  # defensive service boundary: provider failures HOLD
        return _safe_hold(
            normalized_symbol,
            normalized_timeframe,
            f"Market data unavailable: {exc.__class__.__name__}.",
        )

    market_data = _normalize_ohlcv(raw_data)
    if market_data is None or len(market_data) < min_bars:
        rows = 0 if market_data is None else len(market_data)
        return _safe_hold(
            normalized_symbol,
            normalized_timeframe,
            f"Insufficient OHLCV history ({rows}/{min_bars} bars); defaulting to HOLD.",
            metadata={"rows": rows, "min_bars": min_bars},
        )

    close = market_data["Close"]
    rsi_series = TechnicalIndicators.calculate_rsi(close, period=rsi_period)
    macd_line, _macd_signal_line, macd_hist = TechnicalIndicators.calculate_macd(
        close,
        fast=macd_fast,
        slow=macd_slow,
        signal=macd_signal,
    )
    atr_series = TechnicalIndicators.calculate_atr(
        market_data["High"],
        market_data["Low"],
        close,
        period=atr_period,
    )

    rsi = _latest_number(rsi_series)
    macd_current = _latest_number(macd_line)
    macd_previous = _previous_number(macd_line)
    hist_current = _latest_number(macd_hist)
    hist_previous = _previous_number(macd_hist)
    latest_close = _latest_number(close)
    latest_atr = _latest_number(atr_series)

    if None in (rsi, macd_current, macd_previous, hist_current, hist_previous):
        return _safe_hold(
            normalized_symbol,
            normalized_timeframe,
            "Indicator values are incomplete; defaulting to HOLD.",
        )

    macd_delta = macd_current - macd_previous
    hist_delta = hist_current - hist_previous
    macd_improving = macd_delta > 0 and hist_delta > 0
    macd_weakening = macd_delta < 0 and hist_delta < 0
    volatility = _volatility_proxy(latest_atr, latest_close, close)

    if rsi < rsi_lower and macd_improving:
        action = "BUY"
        confidence = _confidence_score(
            action=action,
            rsi=rsi,
            rsi_lower=rsi_lower,
            rsi_upper=rsi_upper,
            trend_alignment=1.0,
            volatility=volatility,
        )
        reason = (
            f"BUY: RSI {rsi:.1f} is below {rsi_lower:.0f}; MACD and histogram "
            f"are improving; volatility proxy is {volatility:.2%}."
        )
    elif rsi > rsi_upper and macd_weakening:
        action = "SELL"
        confidence = _confidence_score(
            action=action,
            rsi=rsi,
            rsi_lower=rsi_lower,
            rsi_upper=rsi_upper,
            trend_alignment=1.0,
            volatility=volatility,
        )
        reason = (
            f"SELL: RSI {rsi:.1f} is above {rsi_upper:.0f}; MACD and histogram "
            f"are weakening; volatility proxy is {volatility:.2%}."
        )
    else:
        action = "HOLD"
        partial_alignment = 0.5 if (macd_delta == 0 or hist_delta == 0) else 0.0
        confidence = _confidence_score(
            action=action,
            rsi=rsi,
            rsi_lower=rsi_lower,
            rsi_upper=rsi_upper,
            trend_alignment=partial_alignment,
            volatility=volatility,
        )
        reason = (
            f"HOLD: RSI {rsi:.1f}, MACD delta {macd_delta:.4f}, histogram delta "
            f"{hist_delta:.4f}, and volatility proxy {volatility:.2%} do not align "
            "with BUY/SELL rules."
        )

    return SignalDecision(
        symbol=normalized_symbol,
        action=action,
        confidence=confidence,
        explanation=reason,
        metadata={
            "engine": "deterministic_rules_v1",
            "timeframe": normalized_timeframe,
            "rsi": rsi,
            "macd": macd_current,
            "macd_previous": macd_previous,
            "macd_histogram": hist_current,
            "macd_histogram_previous": hist_previous,
            "volatility_proxy": volatility,
            "price": latest_close or 0.0,
            "rows": len(market_data),
        },
    )


def decision_to_signal_values(decision: SignalDecision) -> dict[str, float | str]:
    """Extract persistence-safe Signal column values from a decision.

    Generated decisions keep indicator snapshots in metadata so API endpoints can
    persist the MVP ``Signal`` row without adding new nullable/non-nullable DB
    columns. Missing provider/indicator values fall back to ``0.0`` to preserve
    the legacy manual signal table contract during defensive HOLD decisions.
    """

    metadata = decision.metadata
    return {
        "symbol": decision.symbol,
        "action": decision.action,
        "price": _coerce_float(metadata.get("price")) or 0.0,
        "rsi": _coerce_float(metadata.get("rsi")) or 0.0,
        "macd": _coerce_float(metadata.get("macd")) or 0.0,
    }


def generate_signal_decision(
    symbol: str,
    market_snapshot: Mapping[str, Any] | None = None,
    strategy_context: Mapping[str, Any] | None = None,
) -> SignalDecision:
    """Generate a simple deterministic signal decision from an in-memory snapshot.

    This legacy facade is retained for older endpoint/tests while the new
    ``generate_signal`` service owns provider-backed MVP rules.
    """

    snapshot = dict(market_snapshot or {})
    context = dict(strategy_context or {})
    rsi = _coerce_float(snapshot.get("rsi", context.get("rsi")))

    if rsi is not None and rsi < DEFAULT_RSI_LOWER:
        action = "BUY"
        confidence = 0.6
        explanation = "Snapshot decision: RSI below oversold threshold."
    elif rsi is not None and rsi > DEFAULT_RSI_UPPER:
        action = "SELL"
        confidence = 0.6
        explanation = "Snapshot decision: RSI above overbought threshold."
    else:
        action = "HOLD"
        confidence = 0.5
        explanation = "Snapshot decision: no full market-data context provided."

    return SignalDecision(
        symbol=symbol.upper(),
        action=action,
        confidence=confidence,
        explanation=explanation,
        metadata={"engine": "placeholder", "rsi": rsi},
    )


def _safe_hold(
    symbol: str,
    timeframe: str,
    explanation: str,
    metadata: Mapping[str, Any] | None = None,
) -> SignalDecision:
    merged_metadata = {
        "engine": "deterministic_rules_v1",
        "timeframe": timeframe,
        "safe_default": True,
    }
    merged_metadata.update(dict(metadata or {}))
    return SignalDecision(
        symbol=symbol,
        action="HOLD",
        confidence=0.0,
        explanation=explanation,
        metadata=merged_metadata,
    )


def _normalize_ohlcv(data: Any) -> pd.DataFrame | None:
    if data is None:
        return None
    frame = pd.DataFrame(data).copy()
    if frame.empty:
        return None

    rename_map = {str(column).lower(): column for column in frame.columns}
    required = {}
    for canonical in ("Open", "High", "Low", "Close", "Volume"):
        source = rename_map.get(canonical.lower())
        if source is None:
            return None
        required[source] = canonical

    frame = frame.rename(columns=required)
    for column in ("Open", "High", "Low", "Close", "Volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
    return frame if not frame.empty else None


def _confidence_score(
    *,
    action: str,
    rsi: float,
    rsi_lower: float,
    rsi_upper: float,
    trend_alignment: float,
    volatility: float,
) -> float:
    volatility_score = 1.0 - min(max(volatility, 0.0) / 0.05, 1.0)
    if action == "BUY":
        rsi_strength = min(max((rsi_lower - rsi) / max(rsi_lower, 1.0), 0.0), 1.0)
        confidence = (
            0.35
            + (0.35 * rsi_strength)
            + (0.2 * trend_alignment)
            + (0.1 * volatility_score)
        )
    elif action == "SELL":
        rsi_strength = min(
            max((rsi - rsi_upper) / max(100.0 - rsi_upper, 1.0), 0.0),
            1.0,
        )
        confidence = (
            0.35
            + (0.35 * rsi_strength)
            + (0.2 * trend_alignment)
            + (0.1 * volatility_score)
        )
    else:
        threshold_distance = min(abs(rsi - rsi_lower), abs(rsi - rsi_upper))
        neutral_strength = min(
            max(threshold_distance / max(rsi_upper - rsi_lower, 1.0), 0.0),
            1.0,
        )
        confidence = (
            0.25
            + (0.25 * neutral_strength)
            + (0.1 * trend_alignment)
            + (0.1 * volatility_score)
        )
    return _clamp(confidence)


def _volatility_proxy(
    latest_atr: float | None,
    latest_close: float | None,
    close: pd.Series,
) -> float:
    if latest_atr is not None and latest_close not in (None, 0):
        return max(latest_atr / abs(latest_close), 0.0)
    returns = close.pct_change().dropna()
    if returns.empty:
        return 0.0
    return max(float(returns.tail(DEFAULT_ATR_PERIOD).std() or 0.0), 0.0)


def _latest_number(series: pd.Series) -> float | None:
    values = pd.Series(series).dropna()
    if values.empty:
        return None
    return _coerce_float(values.iloc[-1])


def _previous_number(series: pd.Series) -> float | None:
    values = pd.Series(series).dropna()
    if len(values) < 2:
        return None
    return _coerce_float(values.iloc[-2])


def _setting_float(settings: Mapping[str, Any], key: str, default: float) -> float:
    return _coerce_float(settings.get(key)) or default


def _setting_int(settings: Mapping[str, Any], key: str, default: int) -> int:
    value = _coerce_float(settings.get(key))
    if value is None or value <= 0:
        return default
    return int(value)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, round(float(value), 4)))


__all__ = [
    "SignalDecision",
    "decision_to_signal_values",
    "generate_signal",
    "generate_signal_decision",
]
