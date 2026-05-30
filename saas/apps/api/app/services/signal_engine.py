"""Deterministic facade for signal decision generation.

This module intentionally does not replace the legacy signal endpoint logic yet.
It provides a stable bounded-context seam that later PRs can wire into routers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class SignalDecision:
    """Serializable trading-signal decision DTO.

    The DTO stays dataclass-first while exposing ``model_dump``/``dict`` helpers
    compatible with the subset of Pydantic serialization commonly used by the
    application and tests.
    """

    symbol: str
    action: str
    confidence: float
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the decision."""

        return asdict(self)

    def dict(self) -> dict[str, Any]:
        """Pydantic v1-style serialization alias."""

        return self.model_dump()


def generate_signal_decision(
    symbol: str,
    market_snapshot: Mapping[str, Any] | None = None,
    strategy_context: Mapping[str, Any] | None = None,
) -> SignalDecision:
    """Generate a placeholder deterministic signal decision.

    The facade deliberately favors stable, explainable placeholder behavior over
    introducing new trading logic. If a numeric ``rsi`` is available in either
    input mapping, it is used for a simple deterministic BUY/SELL/HOLD choice;
    otherwise the decision is HOLD.
    """

    snapshot = dict(market_snapshot or {})
    context = dict(strategy_context or {})
    rsi = _coerce_float(snapshot.get("rsi", context.get("rsi")))

    if rsi is not None and rsi < 30:
        action = "BUY"
        confidence = 0.6
        rationale = "Placeholder decision: RSI below oversold threshold."
    elif rsi is not None and rsi > 70:
        action = "SELL"
        confidence = 0.6
        rationale = "Placeholder decision: RSI above overbought threshold."
    else:
        action = "HOLD"
        confidence = 0.5
        rationale = "Placeholder decision: no bounded-context strategy wired yet."

    return SignalDecision(
        symbol=symbol.upper(),
        action=action,
        confidence=confidence,
        rationale=rationale,
        metadata={"engine": "placeholder", "rsi": rsi},
    )


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["SignalDecision", "generate_signal_decision"]
