"""Celery application configuration and background tasks."""

from datetime import datetime
from celery import Celery
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD

from app.core.config import settings
from app.services.notifications import NotificationService
from app.db.session import SessionLocal
from app.models import EquitySnapshot, Trade


celery_app = Celery(
    "adc_tasks",
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


@celery_app.task
def run_trading_engine(user_id: int, symbol: str, timeframe: str) -> dict[str, object]:
    """Run the AI trading engine and return the latest signal decision."""

    try:
        data = yf.download(symbol, period="2y", interval=timeframe or "1d")
        if data.empty or "Close" not in data:
            return {"error": f"No market data returned for {symbol}"}

        close_series = data["Close"].squeeze().dropna()
        if len(close_series) < 35:
            return {"error": f"Not enough close-price data returned for {symbol}"}

        rsi = RSIIndicator(close=close_series, window=14)
        macd = MACD(close=close_series)

        current_rsi = float(rsi.rsi().iloc[-1])
        current_macd = float(macd.macd().iloc[-1])
        current_signal = float(macd.macd_signal().iloc[-1])
        current_price = float(close_series.iloc[-1])

        action = "HOLD"
        if current_rsi < 30 and current_macd < current_signal:
            action = "BUY"
        elif current_rsi > 70 and current_macd > current_signal:
            action = "SELL"

        return {
            "user_id": user_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "action": action,
            "price": current_price,
            "rsi": current_rsi,
            "macd": current_macd,
        }
    except Exception as exc:  # pragma: no cover - task errors are returned to callers.
        return {"error": str(exc)}


@celery_app.task
def send_email_notification(
    user_email: str,
    subject: str,
    body: str,
    attachments: list[str] | None = None,
) -> dict[str, object]:
    """Send an HTML email notification to a user with optional attachments."""

    try:
        result = NotificationService(settings=settings).send_email(
            recipients=user_email,
            subject=subject,
            body=body,
            html_body=body,
            attachments=attachments,
        )
        return result.to_dict()
    except Exception as exc:  # pragma: no cover - task errors are returned to callers.
        return {"status": "error", "error": str(exc)}


@celery_app.task
def update_equity_snapshots(user_id: int) -> dict[str, str]:
    """Update a user's equity and drawdown snapshot from closed trades."""

    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(Trade.user_id == user_id).all()
        closed_trades = [
            trade
            for trade in trades
            if trade.status == "closed" and trade.pnl is not None
        ]

        base_balance = 10000.0
        current_balance = base_balance + sum(trade.pnl for trade in closed_trades)

        running_balance = base_balance
        running_max = base_balance
        for trade in closed_trades:
            running_balance += trade.pnl or 0.0
            running_max = max(running_max, running_balance)

        drawdown = (
            (current_balance - running_max) / running_max if running_max > 0 else 0.0
        )

        snapshot = EquitySnapshot(
            user_id=user_id,
            balance=current_balance,
            equity=current_balance,
            drawdown=drawdown,
            timestamp=datetime.utcnow(),
        )
        db.add(snapshot)
        db.commit()
        return {"status": "updated"}
    finally:
        db.close()
