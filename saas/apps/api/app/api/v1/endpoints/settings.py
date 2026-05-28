"""Settings API endpoints."""

from fastapi import APIRouter

from app.core.config import settings as app_settings

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
