"""Tests for the signal-engine bounded-context facade."""

from app.services.signal_engine import SignalDecision, generate_signal_decision


def test_signal_decision_is_serializable() -> None:
    decision = SignalDecision(
        symbol="EURUSD",
        action="HOLD",
        confidence=0.5,
        rationale="test",
    )

    assert decision.model_dump() == decision.dict()
    assert decision.model_dump()["symbol"] == "EURUSD"


def test_generate_signal_decision_is_deterministic_placeholder() -> None:
    decision = generate_signal_decision("eurusd", {"rsi": 50})

    assert decision.symbol == "EURUSD"
    assert decision.action == "HOLD"
    assert decision.confidence == 0.5
    assert decision.metadata["engine"] == "placeholder"


def test_generate_signal_decision_uses_rsi_thresholds() -> None:
    assert generate_signal_decision("AAPL", {"rsi": 25}).action == "BUY"
    assert generate_signal_decision("AAPL", {"rsi": 75}).action == "SELL"
