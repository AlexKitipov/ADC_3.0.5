"""Celery application configuration for background work."""

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "adc_trading_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)
