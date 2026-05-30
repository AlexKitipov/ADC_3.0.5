"""Trading-session lifecycle API endpoints."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models import User
from app.schemas.sessions import (
    SessionEventRead,
    TradingSessionConfigSchema,
    TradingSessionCreate,
    TradingSessionState,
)
from app.security import get_current_user
from app.services.trading_session import (
    TradingSession,
    TradingSessionConfig,
    create_trading_session,
)

router = APIRouter()

# TradingSession instances contain live broker/streaming objects and background
# threads, so the first implementation intentionally keeps them in process
# memory. State is scoped to the authenticated user and can be replaced by a
# durable audit/event repository without changing the HTTP contract.
_sessions: dict[str, dict[str, Any]] = {}
_current_session_by_user: dict[int, str] = {}
_sessions_lock = Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _config_from_schema(config: TradingSessionConfigSchema) -> TradingSessionConfig:
    return TradingSessionConfig(**config.model_dump())


def _session_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Trading session not found"
    )


def _get_record(session_id: str, user_id: int) -> dict[str, Any]:
    record = _sessions.get(session_id)
    if record is None or record["user_id"] != user_id:
        raise _session_not_found()
    return record


def _status_for(record: dict[str, Any]) -> str:
    session: TradingSession = record["session"]
    if session.is_trading_active:
        return "running"
    return "stopped" if record.get("stopped_at") else "created"


def _serialize_session(session_id: str, record: dict[str, Any]) -> TradingSessionState:
    session: TradingSession = record["session"]
    return TradingSessionState(
        id=session_id,
        status=_status_for(record),
        is_trading_active=session.is_trading_active,
        broker_trade_allowed=session.broker_api.is_trade_allowed(),
        symbol=session.symbol,
        config=TradingSessionConfigSchema(**asdict(session.config)),
        last_tick=session.last_tick,
        last_action=session.last_action,
        open_positions=len(session.list_open_positions()),
        event_count=len(session.events),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


@router.post("", response_model=TradingSessionState, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: TradingSessionCreate,
    current_user: User = Depends(get_current_user),
) -> TradingSessionState:
    """Create a new user-scoped in-memory trading session."""

    session_id = str(uuid4())
    session = create_trading_session(config=_config_from_schema(payload.config))
    now = _utc_now()
    record: dict[str, Any] = {
        "user_id": current_user.id,
        "session": session,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "stopped_at": None,
    }

    with _sessions_lock:
        previous_id = _current_session_by_user.get(current_user.id)
        if previous_id:
            previous = _sessions.get(previous_id)
            if previous is not None:
                previous["session"].stop()
                previous["stopped_at"] = _utc_now()
                previous["updated_at"] = previous["stopped_at"]
        _sessions[session_id] = record
        _current_session_by_user[current_user.id] = session_id

    if payload.auto_start:
        session.start()
        record["started_at"] = _utc_now()
        record["stopped_at"] = None
        record["updated_at"] = record["started_at"]

    return _serialize_session(session_id, record)


@router.get("/current", response_model=TradingSessionState)
def get_current_session(
    current_user: User = Depends(get_current_user),
) -> TradingSessionState:
    """Return the authenticated user's current trading session."""

    session_id = _current_session_by_user.get(current_user.id)
    if not session_id:
        raise _session_not_found()
    record = _get_record(session_id, current_user.id)
    return _serialize_session(session_id, record)


@router.post("/{session_id}/start", response_model=TradingSessionState)
def start_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> TradingSessionState:
    """Start market streaming and broker trading for a session."""

    record = _get_record(session_id, current_user.id)
    session: TradingSession = record["session"]
    session.start()
    if record.get("started_at") is None:
        record["started_at"] = _utc_now()
    record["stopped_at"] = None
    record["updated_at"] = _utc_now()
    return _serialize_session(session_id, record)


@router.post("/{session_id}/stop", response_model=TradingSessionState)
def stop_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> TradingSessionState:
    """Stop market streaming for a session while retaining its event history."""

    record = _get_record(session_id, current_user.id)
    session: TradingSession = record["session"]
    session.stop()
    record["stopped_at"] = _utc_now()
    record["updated_at"] = record["stopped_at"]
    return _serialize_session(session_id, record)


@router.get("/{session_id}/events", response_model=list[SessionEventRead])
def list_session_events(
    session_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[SessionEventRead]:
    """Return newest session events in chronological order."""

    record = _get_record(session_id, current_user.id)
    session: TradingSession = record["session"]
    events = session.events[-limit:]
    return [SessionEventRead(**asdict(event)) for event in events]
