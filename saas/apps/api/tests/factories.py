"""Reusable test data helpers for backend API integration flows."""

from __future__ import annotations

from uuid import uuid4

from app.models import default_user_settings_values

TEST_PASSWORD = "correct-horse-battery-staple"


def unique_user_payload(prefix: str = "smoke-user") -> dict[str, str]:
    """Return a unique registration payload for API endpoint tests."""

    suffix = uuid4().hex
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "username": f"{prefix}_{suffix}",
        "password": TEST_PASSWORD,
    }


def auth_headers(token: str) -> dict[str, str]:
    """Return bearer-token authorization headers for authenticated requests."""

    return {"Authorization": f"Bearer {token}"}


def user_settings_payload(**overrides: object) -> dict[str, object]:
    """Return a complete user-settings update payload with optional overrides."""

    settings = default_user_settings_values()
    settings.update(overrides)
    return settings
