"""Tests for persistent trade journal/reporting artifacts."""

import json
from pathlib import Path

import pandas as pd

from app.services.trade_journal import TradeJournal


def test_trade_journal_saves_all_core_artifacts(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path)
    trades = pd.DataFrame(
        [
            {"pnl": 25.0, "balance_after": 10025.0, "exit_reason": "tp"},
            {"pnl": -10.0, "balance_after": 10015.0, "exit_reason": "sl"},
        ]
    )
    equity = pd.Series([10000.0, 10025.0, 10015.0], dtype="float64")
    drawdown = journal.calculate_drawdown(equity)
    performance = journal.calculate_performance(trades, equity)

    paths = journal.save_report(
        trades=trades,
        pending_orders=[{"type": "Buy Stop", "entry_price": 1.101}],
        equity_curve=equity,
        drawdown=drawdown,
        rewards=[{"Step": 0, "Reward": 0.1}],
        performance=performance,
        actions=[{"Action": "Buy Stop", "Action_Id": 1}],
    )

    assert paths.trades_path.exists()
    assert paths.pending_orders_path.exists()
    assert paths.equity_curve_path.exists()
    assert paths.drawdown_path.exists()
    assert paths.rewards_path.exists()
    assert paths.performance_path.exists()
    assert paths.action_journal_path.exists()
    assert json.loads(paths.performance_path.read_text())["total_trades"] == 2


def test_trade_journal_writes_empty_pending_order_headers(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path)

    path = journal.save_pending_orders([])

    saved = pd.read_csv(path)
    assert list(saved.columns)[:3] == ["created_step", "grid_id", "type"]
