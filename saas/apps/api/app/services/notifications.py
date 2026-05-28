"""Email notification backend service for ADC simulation results.

The service centralizes SMTP delivery, attachment handling, and completed-run
result emails.  It intentionally keeps the public API independent from Celery so
it can be used by request handlers, workers, or tests with an injected SMTP
client factory.
"""

from __future__ import annotations

import mimetypes
import smtplib
from dataclasses import asdict, dataclass, field, is_dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from app.core.config import Settings, settings as default_settings

SMTPFactory = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class NotificationAttachment:
    """File attachment descriptor used by the notification service."""

    path: Path
    filename: str | None = None
    content_type: str | None = None

    @classmethod
    def from_path(cls, value: str | Path) -> "NotificationAttachment":
        """Create an attachment descriptor from a filesystem path."""

        return cls(path=Path(value))


@dataclass(slots=True)
class NotificationDeliveryResult:
    """SMTP delivery outcome returned to callers and Celery tasks."""

    status: str
    recipients: list[str]
    subject: str
    attached_files: list[str] = field(default_factory=list)
    skipped_attachments: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        return asdict(self)


class NotificationError(RuntimeError):
    """Raised when a notification cannot be prepared or delivered."""


class NotificationService:
    """Send application emails and simulation result notifications."""

    def __init__(
        self,
        settings: Settings = default_settings,
        smtp_factory: SMTPFactory = smtplib.SMTP,
    ) -> None:
        self.settings = settings
        self.smtp_factory = smtp_factory

    def send_email(
        self,
        *,
        recipients: str | Sequence[str],
        subject: str,
        body: str,
        html_body: str | None = None,
        attachments: Iterable[str | Path | NotificationAttachment] | None = None,
        cc: str | Sequence[str] | None = None,
        bcc: str | Sequence[str] | None = None,
    ) -> NotificationDeliveryResult:
        """Send an email with optional plain-text/HTML bodies and attachments.

        Missing attachment paths are skipped and reported in the delivery result
        instead of failing the entire notification. SMTP errors are returned as a
        structured ``error`` value so async workers can serialize the failure.
        """

        to_recipients = self._normalize_recipients(recipients)
        cc_recipients = self._normalize_recipients(cc)
        bcc_recipients = self._normalize_recipients(bcc)
        if not to_recipients:
            raise NotificationError("At least one recipient is required")
        if not subject.strip():
            raise NotificationError("Email subject is required")

        message = EmailMessage()
        message["From"] = self.settings.FROM_EMAIL
        message["To"] = ", ".join(to_recipients)
        if cc_recipients:
            message["Cc"] = ", ".join(cc_recipients)
        message["Subject"] = subject
        message.set_content(body or "")
        if html_body:
            message.add_alternative(html_body, subtype="html")

        attached_files, skipped_attachments = self._attach_files(message, attachments)
        all_recipients = to_recipients + cc_recipients + bcc_recipients

        try:
            with self.smtp_factory(
                self.settings.SMTP_SERVER,
                self.settings.SMTP_PORT,
                timeout=self.settings.SMTP_TIMEOUT,
            ) as server:
                if self.settings.SMTP_USE_TLS:
                    server.starttls()
                if self.settings.SMTP_USERNAME and self.settings.SMTP_PASSWORD:
                    server.login(
                        self.settings.SMTP_USERNAME,
                        self.settings.SMTP_PASSWORD,
                    )
                server.send_message(
                    message,
                    from_addr=self.settings.FROM_EMAIL,
                    to_addrs=all_recipients,
                )
        except Exception as exc:  # pragma: no cover - serializable worker errors.
            return NotificationDeliveryResult(
                status="error",
                recipients=all_recipients,
                subject=subject,
                attached_files=attached_files,
                skipped_attachments=skipped_attachments,
                error=str(exc),
            )

        return NotificationDeliveryResult(
            status="sent",
            recipients=all_recipients,
            subject=subject,
            attached_files=attached_files,
            skipped_attachments=skipped_attachments,
        )

    def notify_simulation_results(
        self,
        *,
        recipients: str | Sequence[str],
        simulation_result: Any,
        subject: str | None = None,
        body: str | None = None,
        extra_attachments: Iterable[str | Path | NotificationAttachment] | None = None,
    ) -> NotificationDeliveryResult:
        """Email a completed simulation summary with generated result artifacts."""

        result = self._result_to_mapping(simulation_result)
        performance = (
            result.get("performance")
            if isinstance(result.get("performance"), Mapping)
            else {}
        )
        symbol = performance.get("symbol") or result.get("symbol") or "ADC"
        message_subject = subject or f"ADC simulation results - {symbol}"
        message_body = body or self._build_result_body(result, performance)
        attachments = self._simulation_attachments(result)
        if extra_attachments:
            attachments.extend(extra_attachments)

        return self.send_email(
            recipients=recipients,
            subject=message_subject,
            body=message_body,
            attachments=attachments,
        )

    def _attach_files(
        self,
        message: EmailMessage,
        attachments: Iterable[str | Path | NotificationAttachment] | None,
    ) -> tuple[list[str], list[str]]:
        attached_files: list[str] = []
        skipped_attachments: list[str] = []
        for raw_attachment in attachments or []:
            attachment = self._normalize_attachment(raw_attachment)
            path = attachment.path
            if not path.exists() or not path.is_file():
                skipped_attachments.append(str(path))
                continue

            content_type = (
                attachment.content_type
                or mimetypes.guess_type(path.name)[0]
                or "application/octet-stream"
            )
            maintype, subtype = content_type.split("/", 1)
            message.add_attachment(
                path.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=attachment.filename or path.name,
            )
            attached_files.append(str(path))
        return attached_files, skipped_attachments

    @staticmethod
    def _normalize_attachment(
        attachment: str | Path | NotificationAttachment,
    ) -> NotificationAttachment:
        if isinstance(attachment, NotificationAttachment):
            return attachment
        return NotificationAttachment.from_path(attachment)

    @staticmethod
    def _normalize_recipients(recipients: str | Sequence[str] | None) -> list[str]:
        if recipients is None:
            return []
        if isinstance(recipients, str):
            candidates = recipients.replace(";", ",").split(",")
        else:
            candidates = list(recipients)
        return [
            recipient.strip()
            for recipient in candidates
            if recipient and recipient.strip()
        ]

    @staticmethod
    def _result_to_mapping(simulation_result: Any) -> Mapping[str, Any]:
        if isinstance(simulation_result, Mapping):
            return simulation_result
        if hasattr(simulation_result, "to_dict"):
            return simulation_result.to_dict()
        if is_dataclass(simulation_result):
            return asdict(simulation_result)
        raise NotificationError(
            "simulation_result must be a mapping, dataclass, or expose to_dict()"
        )

    @staticmethod
    def _simulation_attachments(result: Mapping[str, Any]) -> list[Path]:
        path_keys = [
            "historical_data_path",
            "generated_data_path",
            "orders_path",
            "trades_path",
            "performance_path",
            "rewards_path",
            "equity_curve_path",
            "drawdown_path",
            "equity_chart_path",
            "drawdown_chart_path",
            "model_path",
        ]
        return [Path(value) for key in path_keys if (value := result.get(key))]

    @staticmethod
    def _build_result_body(
        result: Mapping[str, Any], performance: Mapping[str, Any]
    ) -> str:
        lines = [
            "Здравейте,",
            "",
            "Прикачени са резултатите от завършената ADC симулация.",
            "",
            "Обобщение:",
        ]
        summary = {
            "Symbol": performance.get("symbol") or result.get("symbol"),
            "Total steps": result.get("total_steps"),
            "Total trades": performance.get("total_trades"),
            "Final equity": performance.get("final_equity"),
            "Max drawdown": performance.get("max_drawdown"),
            "Win rate": performance.get("win_rate"),
            "LSTM trained": result.get("trained_lstm"),
            "RL trained": result.get("trained_rl"),
        }
        for label, value in summary.items():
            if value is not None:
                lines.append(f"- {label}: {value}")
        lines.extend(["", "Поздрави,", "ADC Notification Service"])
        return "\n".join(lines)
