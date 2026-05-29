"""Settings API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.db import get_db
from app.models import User, UserSettings, default_user_settings_values
from app.schemas import UserSettings as UserSettingsSchema, UserSettingsUpdate
from app.security import get_current_user

router = APIRouter()


def get_or_create_user_settings(user_id: int, db: Session) -> UserSettings:
    """Return persisted settings, creating defaults for first-time users."""

    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    if settings is None:
        settings = UserSettings(
            user_id=user_id,
            **default_user_settings_values(),
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.get("")
def read_settings() -> dict[str, str]:
    """Return safe, non-secret runtime settings."""

    return {
        "app_name": app_settings.APP_NAME,
        "app_env": app_settings.APP_ENV,
        "algorithm": app_settings.ALGORITHM,
        "from_email": app_settings.FROM_EMAIL,
    }


@router.get("/user-settings", response_model=UserSettingsSchema)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettings:
    """Return trading and notification settings for the authenticated user."""

    return get_or_create_user_settings(current_user.id, db)


@router.put("/user-settings", response_model=UserSettingsSchema)
def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettings:
    """Fully replace the authenticated user's settings.

    ``risk_per_trade`` and ``grid_step_pct`` use decimal fraction semantics:
    0.02 means 2%, and 0.005 means 0.5%.
    """

    settings = get_or_create_user_settings(current_user.id, db)

    for key, value in settings_update.model_dump().items():
        setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    return settings
