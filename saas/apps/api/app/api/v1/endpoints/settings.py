"""Settings API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.db import get_db
from app.models import User, UserSettings
from app.schemas import UserSettings as UserSettingsSchema, UserSettingsUpdate
from app.security import get_current_user

router = APIRouter()


@router.get("")
def read_settings() -> dict[str, str]:
    """Return safe, non-secret runtime settings."""

    return {
        "app_name": app_settings.APP_NAME,
        "app_env": app_settings.APP_ENV,
        "algorithm": app_settings.ALGORITHM,
        "from_email": app_settings.FROM_EMAIL,
    }


@router.get("/user-settings", response_model=UserSettingsSchema | None)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettings | None:
    """Return trading and notification settings for the authenticated user."""

    settings = (
        db.query(UserSettings)
        .filter(UserSettings.user_id == current_user.id)
        .first()
    )
    return settings


@router.put("/user-settings", response_model=dict[str, str])
def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Create or replace the authenticated user's settings."""

    settings = (
        db.query(UserSettings)
        .filter(UserSettings.user_id == current_user.id)
        .first()
    )

    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    for key, value in settings_update.model_dump().items():
        setattr(settings, key, value)

    db.commit()
    return {"message": "Settings updated successfully"}
