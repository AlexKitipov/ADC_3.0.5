"""Background worker modules."""

from app.workers.celery import celery_app

__all__ = ["celery_app"]
