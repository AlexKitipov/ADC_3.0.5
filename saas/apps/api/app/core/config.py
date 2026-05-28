"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the ADC Trading Platform API."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ADC Trading Platform"
    APP_ENV: str = "local"
    DATABASE_URL: str = "sqlite:///./adc_saas.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = Field(
        default="change-me", validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET")
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-app-password"
    FROM_EMAIL: str = "noreply@adctrading.com"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


settings = get_settings()
