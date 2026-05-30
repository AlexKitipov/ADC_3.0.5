"""Live market stream API endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Path as FastAPIPath, Query, Request
from fastapi.responses import StreamingResponse

from app.schemas import MarketTickSchema
from app.services.market_stream import MockWebSocketClient
from app.services.order_management import MockBrokerAPI

router = APIRouter()


def _sse_event(event: str, payload: dict[str, object]) -> str:
    """Format a Server-Sent Event frame."""

    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.get(
    "/{symbol}",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Server-Sent Events stream of MarketTick payloads.",
        }
    },
)
async def stream_market_ticks(
    request: Request,
    symbol: Annotated[str, FastAPIPath(min_length=1, max_length=32)],
    interval: Annotated[float, Query(ge=0.1, le=30.0)] = 1.0,
    max_ticks: Annotated[int | None, Query(ge=1, le=500)] = None,
) -> StreamingResponse:
    """Stream mock market ticks for a symbol using Server-Sent Events."""

    normalized_symbol = symbol.strip().upper()

    async def events() -> AsyncIterator[str]:
        broker = MockBrokerAPI()
        client = MockWebSocketClient(
            broker_api=broker,
            symbol=normalized_symbol,
            stream_interval=interval,
        )
        emitted_ticks = 0

        yield _sse_event(
            "connected",
            {"symbol": normalized_symbol, "message": "market stream connected"},
        )

        while max_ticks is None or emitted_ticks < max_ticks:
            if await request.is_disconnected():
                break

            tick = MarketTickSchema.model_validate(client.generate_tick().to_dict())
            yield _sse_event("tick", tick.model_dump(mode="json"))
            emitted_ticks += 1
            await asyncio.sleep(interval)

        yield _sse_event(
            "closed",
            {"symbol": normalized_symbol, "message": "market stream closed"},
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
