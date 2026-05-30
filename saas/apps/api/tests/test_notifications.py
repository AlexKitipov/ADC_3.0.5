"""Tests for email notification service behavior."""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.notifications import get_notification_service
from app.core.config import Settings
from app.main import app
from app.services.notifications import NotificationError, NotificationService


class FakeSMTP:
    """Capture SMTP calls without opening a network connection."""

    instances: list["FakeSMTP"] = []

    def __init__(self, server: str, port: int, timeout: int) -> None:
        self.server = server
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.sent_messages: list[dict[str, Any]] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(
        self, message: object, from_addr: str, to_addrs: list[str]
    ) -> None:
        self.sent_messages.append(
            {"message": message, "from_addr": from_addr, "to_addrs": to_addrs}
        )


@pytest.fixture(autouse=True)
def reset_fake_smtp() -> None:
    FakeSMTP.instances.clear()


def make_settings() -> Settings:
    return Settings(
        SMTP_SERVER="smtp.test.local",
        SMTP_PORT=2525,
        SMTP_TIMEOUT=7,
        SMTP_USE_TLS=True,
        SMTP_USERNAME="robot@example.com",
        SMTP_PASSWORD="secret",
        FROM_EMAIL="noreply@example.com",
    )


def test_send_email_attaches_existing_files_and_reports_missing(tmp_path: Path) -> None:
    report = tmp_path / "performance.json"
    report.write_text('{"total_trades": 2}\n')
    missing = tmp_path / "missing.csv"

    result = NotificationService(
        settings=make_settings(), smtp_factory=FakeSMTP
    ).send_email(
        recipients="user@example.com",
        subject="ADC report",
        body="See attached",
        attachments=[report, missing],
    )

    assert result.status == "sent"
    assert result.recipients == ["user@example.com"]
    assert result.attached_files == [str(report)]
    assert result.skipped_attachments == [str(missing)]
    smtp = FakeSMTP.instances[0]
    assert smtp.server == "smtp.test.local"
    assert smtp.port == 2525
    assert smtp.timeout == 7
    assert smtp.started_tls is True
    assert smtp.login_args == ("robot@example.com", "secret")
    assert smtp.sent_messages[0]["to_addrs"] == ["user@example.com"]


def test_notify_simulation_results_uses_result_artifacts(tmp_path: Path) -> None:
    historical = tmp_path / "historical_df.csv"
    trades = tmp_path / "trades_v2.csv"
    performance = tmp_path / "performance_v2.json"
    for path in [historical, trades, performance]:
        path.write_text("ok\n")

    result = NotificationService(
        settings=make_settings(), smtp_factory=FakeSMTP
    ).notify_simulation_results(
        recipients=["one@example.com", "two@example.com"],
        simulation_result={
            "historical_data_path": str(historical),
            "trades_path": str(trades),
            "performance_path": str(performance),
            "total_steps": 42,
            "trained_lstm": False,
            "trained_rl": True,
            "performance": {
                "symbol": "EURUSD",
                "total_trades": 3,
                "final_equity": 10025.0,
            },
        },
    )

    assert result.status == "sent"
    assert result.subject == "ADC simulation results - EURUSD"
    assert result.recipients == ["one@example.com", "two@example.com"]
    assert set(result.attached_files) == {
        str(historical),
        str(trades),
        str(performance),
    }


def test_send_email_requires_recipient() -> None:
    with pytest.raises(NotificationError):
        NotificationService(
            settings=make_settings(), smtp_factory=FakeSMTP
        ).send_email(
            recipients="",
            subject="ADC report",
            body="Missing recipient",
        )

api_client = TestClient(app)


def register_and_login() -> tuple[str, str]:
    """Create a unique user and return its token plus email."""

    suffix = uuid4().hex
    email = f"notifications_{suffix}@example.com"
    payload = {
        "email": email,
        "username": f"notifications_{suffix}",
        "password": "correct-horse-battery-staple",
    }

    register_response = api_client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = api_client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"], email


def auth_headers(token: str) -> dict[str, str]:
    """Return bearer token headers for authenticated notification requests."""

    return {"Authorization": f"Bearer {token}"}


def override_notification_service() -> NotificationService:
    """Return a mocked SMTP notification service for endpoint tests."""

    return NotificationService(settings=make_settings(), smtp_factory=FakeSMTP)


def test_notification_test_endpoint_sends_to_current_user_by_default() -> None:
    token, email = register_and_login()
    app.dependency_overrides[get_notification_service] = override_notification_service

    try:
        response = api_client.post(
            "/api/v1/notifications/test",
            headers=auth_headers(token),
            json={"subject": "SMTP smoke test", "body": "Hello from ADC"},
        )
    finally:
        app.dependency_overrides.pop(get_notification_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sent"
    assert body["recipients"] == [email]
    assert body["subject"] == "SMTP smoke test"
    assert body["attached_files"] == []
    assert body["skipped_attachments"] == []
    assert FakeSMTP.instances[0].sent_messages[0]["to_addrs"] == [email]


def test_simulation_results_endpoint_reports_attachments(tmp_path: Path) -> None:
    token, _ = register_and_login()
    app.dependency_overrides[get_notification_service] = override_notification_service
    performance = tmp_path / "performance.json"
    missing = tmp_path / "missing.csv"
    performance.write_text('{"total_trades": 4}\n')

    try:
        response = api_client.post(
            "/api/v1/notifications/simulation-results",
            headers=auth_headers(token),
            json={
                "recipients": ["ops@example.com"],
                "simulation_result": {
                    "symbol": "BTCUSDT",
                    "performance_path": str(performance),
                    "trades_path": str(missing),
                    "total_steps": 10,
                    "trained_lstm": False,
                    "trained_rl": True,
                    "performance": {"total_trades": 4},
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_notification_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sent"
    assert body["recipients"] == ["ops@example.com"]
    assert body["subject"] == "ADC simulation results - BTCUSDT"
    assert body["attached_files"] == [str(performance)]
    assert body["skipped_attachments"] == [str(missing)]
