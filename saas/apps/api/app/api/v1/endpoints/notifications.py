"""Notification delivery API endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.schemas import (
    NotificationAttachmentReference,
    NotificationDeliveryResponse,
    NotificationTestRequest,
    SimulationResultsNotificationRequest,
)
from app.security import get_current_user
from app.services.notifications import (
    NotificationAttachment,
    NotificationError,
    NotificationService,
)

router = APIRouter()


def get_notification_service() -> NotificationService:
    """Return the configured notification service for dependency overrides."""

    return NotificationService()


@router.post("/test", response_model=NotificationDeliveryResponse)
def send_test_notification(
    request: NotificationTestRequest,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationDeliveryResponse:
    """Send an authenticated user's notification configuration test email."""

    recipients = _recipients_or_current_user(request.recipients, current_user)
    try:
        result = notification_service.send_email(
            recipients=recipients,
            subject=request.subject,
            body=request.body,
            attachments=_to_service_attachments(request.attachments),
        )
    except NotificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return NotificationDeliveryResponse(**result.to_dict())


@router.post("/simulation-results", response_model=NotificationDeliveryResponse)
def send_simulation_results_notification(
    request: SimulationResultsNotificationRequest,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationDeliveryResponse:
    """Send completed simulation result summaries and artifacts by email."""

    recipients = _recipients_or_current_user(request.recipients, current_user)
    try:
        result = notification_service.notify_simulation_results(
            recipients=recipients,
            simulation_result=request.simulation_result,
            subject=request.subject,
            body=request.body,
            extra_attachments=_to_service_attachments(request.extra_attachments),
        )
    except NotificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return NotificationDeliveryResponse(**result.to_dict())


def _recipients_or_current_user(
    recipients: list[str] | None,
    current_user: User,
) -> list[str]:
    if recipients:
        return [str(recipient) for recipient in recipients]
    return [current_user.email]


def _to_service_attachments(
    attachments: list[NotificationAttachmentReference],
) -> list[NotificationAttachment]:
    return [
        NotificationAttachment(
            path=Path(attachment.path),
            filename=attachment.filename,
            content_type=attachment.content_type,
        )
        for attachment in attachments
    ]
