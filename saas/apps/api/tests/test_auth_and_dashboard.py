"""Tests for authenticated account and dashboard endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


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
    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return payload, token


def test_register_login_and_me_round_trip() -> None:
    payload, token = register_and_login()

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == payload["email"]
    assert body["username"] == payload["username"]
    assert body["is_active"] is True


def test_login_rejects_invalid_password() -> None:
    payload = unique_user_payload()
    register_response = client.post("/api/auth/register", json=payload)

    response = client.post(
        "/api/auth/login",
        data={"username": payload["username"], "password": "wrong-password"},
    )

    assert register_response.status_code == 201
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login_requires_oauth2_form_body() -> None:
    payload = unique_user_payload()
    register_response = client.post("/api/auth/register", json=payload)

    response = client.post(
        "/api/auth/login",
        params={"username": payload["username"], "password": payload["password"]},
    )

    assert register_response.status_code == 201
    assert response.status_code == 422


def test_duplicate_registration_rejects_existing_email() -> None:
    payload = unique_user_payload()
    first_response = client.post("/api/auth/register", json=payload)
    second_payload = {**payload, "username": f"different_{uuid4().hex}"}
    second_response = client.post("/api/auth/register", json=second_payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json() == {"detail": "Email already registered"}


def test_protected_dashboard_requires_bearer_token() -> None:
    response = client.get("/api/dashboard/stats")

    assert response.status_code == 401


def test_dashboard_stats_defaults_for_new_user() -> None:
    _payload, token = register_and_login()

    response = client.get(
        "/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"}
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
