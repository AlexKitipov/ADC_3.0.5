"""Notification API request and response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

NotificationDeliveryStatus = Literal["sent", "error"]


class NotificationAttachmentReference(BaseModel):
    """Filesystem attachment reference accepted by notification endpoints."""

    path: str = Field(min_length=1)
    filename: str | None = Field(default=None, min_length=1)
    content_type: str | None = Field(default=None, pattern=r"^[^/]+/[^/]+$")


class NotificationTestRequest(BaseModel):
    """Payload for sending an ad-hoc notification configuration test email."""

    model_config = ConfigDict(extra="forbid")

    recipients: list[EmailStr] | None = None
    subject: str = Field(
        default="ADC notification test", min_length=1, max_length=255
    )
    body: str = Field(
        default="This is a test email from the ADC Trading Platform notification service.",
        min_length=1,
    )
    attachments: list[NotificationAttachmentReference] = Field(default_factory=list)


class SimulationResultsNotificationRequest(BaseModel):
    """Payload for sending completed simulation result artifacts by email."""

    model_config = ConfigDict(extra="forbid")

    recipients: list[EmailStr] | None = None
    simulation_result: dict[str, Any]
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    extra_attachments: list[NotificationAttachmentReference] = Field(
        default_factory=list
    )


class NotificationDeliveryResponse(BaseModel):
    """Structured notification delivery status returned to API callers."""

    status: NotificationDeliveryStatus
    recipients: list[str]
    subject: str
    attached_files: list[str] = Field(default_factory=list)
    skipped_attachments: list[str] = Field(default_factory=list)
    error: str | None = None


__all__ = [
    "NotificationAttachmentReference",
    "NotificationDeliveryResponse",
    "NotificationDeliveryStatus",
    "NotificationTestRequest",
    "SimulationResultsNotificationRequest",
]
