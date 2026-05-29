"""Tests for authenticated account and dashboard endpoints."""

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import EquitySnapshot, User


client = TestClient(app)


def unique_user_payload() -> dict[str, str]:
    """Return a unique registration payload for endpoint tests."""

    suffix = uuid4().hex
    return {
        "email": f"{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": "correct-horse-battery-staple",
    }


def register_and_login() -> tuple[dict[str, str], str]:
    """Create a user and return its registration payload and access token."""

    payload = unique_user_payload()
    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return payload, token


def test_register_login_and_me_round_trip() -> None:
    payload, token = register_and_login()

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == payload["email"]
    assert body["username"] == payload["username"]
    assert body["is_active"] is True


def test_login_rejects_invalid_password() -> None:
    payload = unique_user_payload()
    register_response = client.post("/api/v1/auth/register", json=payload)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": "wrong-password"},
    )

    assert register_response.status_code == 201
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login_requires_oauth2_form_body() -> None:
    payload = unique_user_payload()
    register_response = client.post("/api/v1/auth/register", json=payload)

    response = client.post(
        "/api/v1/auth/login",
        params={"username": payload["username"], "password": payload["password"]},
    )

    assert register_response.status_code == 201
    assert response.status_code == 422


def test_duplicate_registration_rejects_existing_email() -> None:
    payload = unique_user_payload()
    first_response = client.post("/api/v1/auth/register", json=payload)
    second_payload = {**payload, "username": f"different_{uuid4().hex}"}
    second_response = client.post("/api/v1/auth/register", json=second_payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json() == {"detail": "Email already registered"}


def test_protected_dashboard_requires_bearer_token() -> None:
    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 401


def test_dashboard_stats_defaults_for_new_user() -> None:
    _payload, token = register_and_login()

    response = client.get(
        "/api/v1/dashboard/stats", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_balance": 0.0,
        "current_equity": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "total_trades": 0,
        "monthly_pnl": 0.0,
    }


def test_dashboard_curve_endpoints_return_named_contracts() -> None:
    """Curves return timestamped points scoped to the authenticated user."""

    payload, token = register_and_login()
    snapshot_time = datetime.utcnow().replace(microsecond=0) - timedelta(days=1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload["username"]).one()
        db.add(
            EquitySnapshot(
                user_id=user.id,
                balance=10000.0,
                equity=10125.5,
                drawdown=0.025,
                timestamp=snapshot_time,
            )
        )
        db.commit()
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    equity_response = client.get(
        "/api/v1/dashboard/equity-curve", headers=headers, params={"days": 30}
    )
    drawdown_response = client.get(
        "/api/v1/dashboard/drawdown-curve", headers=headers, params={"days": 30}
    )

    assert equity_response.status_code == 200
    assert drawdown_response.status_code == 200
    assert equity_response.json() == [
        {
            "timestamp": snapshot_time.isoformat(),
            "equity": 10125.5,
            "balance": 10000.0,
        }
    ]
    assert drawdown_response.json() == [
        {"timestamp": snapshot_time.isoformat(), "drawdown": 0.025}
    ]


def test_dashboard_curves_are_exposed_with_openapi_response_schemas() -> None:
    openapi_response = client.get("/openapi.json")

    assert openapi_response.status_code == 200
    openapi = openapi_response.json()
    schemas = openapi["components"]["schemas"]
    assert {"EquityCurvePoint", "DrawdownCurvePoint"}.issubset(schemas.keys())
    equity_schema = openapi["paths"]["/api/v1/dashboard/equity-curve"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    drawdown_schema = openapi["paths"]["/api/v1/dashboard/drawdown-curve"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert equity_schema["type"] == "array"
    assert equity_schema["items"] == {"$ref": "#/components/schemas/EquityCurvePoint"}
    assert drawdown_schema["type"] == "array"
    assert drawdown_schema["items"] == {
        "$ref": "#/components/schemas/DrawdownCurvePoint"
    }
