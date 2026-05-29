"""Version 1 API router composition."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, dashboard, settings, signals, simulations, strategy, trades

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(signals.router, prefix="/signals", tags=["Signals"])
api_router.include_router(trades.router, prefix="/trades", tags=["Trades"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["Strategy"])
api_router.include_router(simulations.router, prefix="/simulations", tags=["Simulations"])
