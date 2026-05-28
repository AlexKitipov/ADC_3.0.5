"""FastAPI application entry point for the ADC Trading Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.api.v1.endpoints import (
    auth,
    dashboard,
    settings as settings_routes,
    signals,
    trades,
)
from app.core.config import settings
from app.db import Base, engine
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
    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
    app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
    app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])
    app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])

    @app.get("/api/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/health", tags=["Health"])
    def versioned_health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.state.celery_app = celery_app
    return app


app = create_app()
