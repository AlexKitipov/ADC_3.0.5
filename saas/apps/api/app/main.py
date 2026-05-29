"""FastAPI application entry point for the ADC Trading Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.db import Base, engine
import app.models  # noqa: F401 - register SQLAlchemy models before create_all
from app.workers import celery_app


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title="ADC Trading Platform",
        description="AI-Driven Crypto Trading SaaS",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api/v1/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.state.celery_app = celery_app
    return app


app = create_app()
