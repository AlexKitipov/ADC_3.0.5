"""Version 1 API router composition."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    dashboard,
    indicators,
    lstm,
    market_data,
    orders,
    rl,
    sessions,
    settings,
    signals,
    simulations,
    strategy,
    trades,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(indicators.router, prefix="/indicators", tags=["Indicators"])
api_router.include_router(signals.router, prefix="/signals", tags=["Signals"])
api_router.include_router(trades.router, prefix="/trades", tags=["Trades"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(rl.router, prefix="/rl", tags=["RL Training"])
api_router.include_router(lstm.router, prefix="/lstm", tags=["LSTM Generation"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["Market Data"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["Strategy"])
api_router.include_router(simulations.router, prefix="/simulations", tags=["Simulations"])
