"""Tests for the live market stream endpoint."""

import json

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import MarketTickSchema


def _sse_payloads(body: str, event_name: str) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for frame in body.strip().split("\n\n"):
        lines = frame.splitlines()
        if f"event: {event_name}" not in lines:
            continue
        data_line = next(line for line in lines if line.startswith("data: "))
        payloads.append(json.loads(data_line.removeprefix("data: ")))
    return payloads


def test_market_stream_emits_market_tick_sse_payloads() -> None:
    client = TestClient(app)

    with client.stream(
        "GET", "/api/v1/market-stream/eurusd", params={"interval": 0.1, "max_ticks": 2}
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    ticks = _sse_payloads(body, "tick")
    assert len(ticks) == 2
    assert ticks[0]["symbol"] == "EURUSD"
    assert ticks[0]["bid"] <= ticks[0]["price"] <= ticks[0]["ask"]
    MarketTickSchema.model_validate(ticks[0])


def test_market_stream_rejects_invalid_interval() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/market-stream/EURUSD", params={"interval": 0, "max_ticks": 1}
    )

    assert response.status_code == 422
