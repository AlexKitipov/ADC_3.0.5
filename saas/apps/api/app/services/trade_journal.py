"""Persistent trade journal and reporting utilities.

This module owns the file outputs that the original notebook described as the
``TradeJournal`` directory: closed trades, pending orders, equity curve,
drawdown curve, reward logs, and the performance JSON summary.  Keeping these
writes in one service gives simulations and future API/background tasks the
same deterministic artifact layout.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


TRADE_COLUMNS = [
    "entry_date",
    "exit_date",
    "type",
    "entry_price",
    "exit_price",
    "size",
    "pnl",
    "exit_reason",
    "balance_after",
]

PENDING_ORDER_COLUMNS = [
    "created_step",
    "grid_id",
    "type",
    "entry_price",
    "tp",
    "sl",
    "initial_sl",
    "size",
]

REWARD_COLUMNS = ["Step", "Reward"]
EQUITY_COLUMNS = ["Step", "Equity"]
DRAWDOWN_COLUMNS = ["Step", "Drawdown"]
ACTION_JOURNAL_COLUMNS = [
    "Index",
    "Action",
    "Action_Id",
    "Price",
    "RSI",
    "MACD",
    "MACD_Signal",
]


@dataclass(frozen=True, slots=True)
class TradeJournalPaths:
    """Resolved output locations for one simulation/reporting run."""

    output_dir: Path
    journal_dir: Path
    charts_dir: Path
    trades_path: Path
    pending_orders_path: Path
    equity_curve_path: Path
    drawdown_path: Path
    rewards_path: Path
    performance_path: Path
    action_journal_path: Path
    equity_chart_path: Path
    drawdown_chart_path: Path

    def as_strings(self) -> dict[str, str]:
        """Return JSON-friendly path strings."""

        return {key: str(value) for key, value in asdict(self).items()}


class TradeJournal:
    """Save simulation trades, curves, pending orders, and metrics to disk."""

    def __init__(
        self,
        output_dir: str | Path,
        journal_folder: str = "TradeJournal",
        suffix: str = "v2",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.journal_dir = self.output_dir / journal_folder
        self.charts_dir = self.journal_dir / "charts"
        self.suffix = suffix.strip("_")
        self.paths = self._build_paths()

    def ensure_directories(self) -> TradeJournalPaths:
        """Create the output, journal, and chart directories if needed."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        return self.paths

    def save_trades(self, trades: Any) -> Path:
        """Persist closed trades as a CSV file."""

        frame = self._to_frame(trades, default_columns=TRADE_COLUMNS)
        return self._write_csv(frame, self.paths.trades_path)

    def save_pending_orders(self, pending_orders: Any) -> Path:
        """Persist currently pending broker/grid orders as a CSV file."""

        frame = self._to_frame(pending_orders, default_columns=PENDING_ORDER_COLUMNS)
        return self._write_csv(frame, self.paths.pending_orders_path)

    def save_action_journal(self, actions: Any) -> Path:
        """Persist evaluated policy decisions for debugging and replay."""

        frame = self._to_frame(actions, default_columns=ACTION_JOURNAL_COLUMNS)
        return self._write_csv(frame, self.paths.action_journal_path)

    def save_rewards(self, rewards: Any) -> Path:
        """Persist per-step rewards as a CSV file."""

        frame = self._to_frame(rewards, default_columns=REWARD_COLUMNS)
        return self._write_csv(frame, self.paths.rewards_path)

    def save_equity_curve(self, equity_curve: Any) -> Path:
        """Persist the equity curve as ``Step,Equity`` CSV data."""

        frame = self._curve_to_frame(equity_curve, value_column="Equity")
        return self._write_csv(frame, self.paths.equity_curve_path)

    def save_drawdown(self, drawdown: Any) -> Path:
        """Persist the drawdown curve as ``Step,Drawdown`` CSV data."""

        frame = self._curve_to_frame(drawdown, value_column="Drawdown")
        return self._write_csv(frame, self.paths.drawdown_path)

    def save_performance(self, performance: Mapping[str, Any]) -> Path:
        """Persist performance metrics as stable, pretty-printed JSON."""

        payload = self._json_sanitize(dict(performance))
        self._atomic_write_text(
            self.paths.performance_path,
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
        return self.paths.performance_path

    def save_report(
        self,
        *,
        trades: Any,
        pending_orders: Any,
        equity_curve: Any,
        drawdown: Any,
        rewards: Any,
        performance: Mapping[str, Any],
        actions: Any | None = None,
    ) -> TradeJournalPaths:
        """Persist all journal/report artifacts for one completed run."""

        self.ensure_directories()
        self.save_trades(trades)
        self.save_pending_orders(pending_orders)
        self.save_equity_curve(equity_curve)
        self.save_drawdown(drawdown)
        self.save_rewards(rewards)
        self.save_performance(performance)
        if actions is not None:
            self.save_action_journal(actions)
        return self.paths

    def calculate_drawdown(self, equity_curve: Any) -> pd.Series:
        """Calculate percentage drawdown from an equity curve."""

        equity = pd.to_numeric(pd.Series(equity_curve), errors="coerce").fillna(0.0)
        if equity.empty:
            return pd.Series(dtype="float64")
        rolling_high = equity.cummax().replace(0, np.nan)
        return ((equity - rolling_high) / rolling_high).fillna(0.0)

    def calculate_performance(self, trades: Any, equity_curve: Any) -> dict[str, Any]:
        """Calculate core performance metrics from trades and equity."""

        trades_df = self._to_frame(trades, default_columns=TRADE_COLUMNS)
        equity = pd.to_numeric(pd.Series(equity_curve), errors="coerce").fillna(0.0)
        drawdown = self.calculate_drawdown(equity)
        performance: dict[str, Any] = {
            "total_trades": int(len(trades_df)),
            "max_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
            "final_equity": float(equity.iloc[-1]) if not equity.empty else 0.0,
        }
        if trades_df.empty or "pnl" not in trades_df.columns:
            performance.update(
                {"win_rate": 0.0, "avg_profit": 0.0, "avg_loss": 0.0, "expectancy": 0.0}
            )
            return performance

        pnl = pd.to_numeric(trades_df["pnl"], errors="coerce").fillna(0.0)
        winning = pnl[pnl > 0]
        losing = pnl[pnl < 0]
        win_rate = float(len(winning) / len(pnl)) if len(pnl) else 0.0
        avg_profit = float(winning.mean()) if not winning.empty else 0.0
        avg_loss = float(losing.mean()) if not losing.empty else 0.0
        performance.update(
            {
                "win_rate": win_rate,
                "avg_profit": avg_profit,
                "avg_loss": avg_loss,
                "expectancy": (win_rate * avg_profit) + ((1 - win_rate) * avg_loss),
            }
        )
        return performance

    def _build_paths(self) -> TradeJournalPaths:
        suffix = f"_{self.suffix}" if self.suffix else ""
        return TradeJournalPaths(
            output_dir=self.output_dir,
            journal_dir=self.journal_dir,
            charts_dir=self.charts_dir,
            trades_path=self.journal_dir / f"trades{suffix}.csv",
            pending_orders_path=self.output_dir / f"pending_orders{suffix}.csv",
            equity_curve_path=self.journal_dir / f"equity_curve{suffix}.csv",
            drawdown_path=self.journal_dir / f"drawdown{suffix}.csv",
            rewards_path=self.journal_dir / f"rewards{suffix}.csv",
            performance_path=self.journal_dir / f"performance{suffix}.json",
            action_journal_path=self.journal_dir / f"actions{suffix}.csv",
            equity_chart_path=self.charts_dir / f"equity_curve{suffix}.png",
            drawdown_chart_path=self.charts_dir / f"drawdown{suffix}.png",
        )

    def _to_frame(self, data: Any, default_columns: Sequence[str]) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            frame = data.copy()
        elif data is None:
            frame = pd.DataFrame(columns=list(default_columns))
        else:
            frame = pd.DataFrame(data)

        if frame.empty and len(frame.columns) == 0:
            frame = pd.DataFrame(columns=list(default_columns))
        return frame

    def _curve_to_frame(self, curve: Any, value_column: str) -> pd.DataFrame:
        if isinstance(curve, pd.DataFrame):
            frame = curve.copy()
            if value_column in frame.columns:
                return frame
            if len(frame.columns) == 1:
                frame = frame.rename(columns={frame.columns[0]: value_column})
            if "Step" not in frame.columns:
                frame.insert(0, "Step", range(len(frame)))
            return frame

        series = pd.Series(curve, dtype="float64")
        return pd.DataFrame(
            {"Step": range(len(series)), value_column: series.to_numpy()}
        )

    def _write_csv(self, frame: pd.DataFrame, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        return path

    def _atomic_write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    def _json_sanitize(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): self._json_sanitize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_sanitize(item) for item in value]
        if isinstance(value, (datetime, date, pd.Timestamp)):
            return value.isoformat()
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return [self._json_sanitize(item) for item in value.tolist()]
        if not isinstance(value, (list, tuple, dict, set)):
            try:
                is_missing = pd.isna(value)
            except (TypeError, ValueError):
                is_missing = False
            if isinstance(is_missing, (bool, np.bool_)) and is_missing:
                return None
        return value


__all__ = [
    "ACTION_JOURNAL_COLUMNS",
    "DRAWDOWN_COLUMNS",
    "EQUITY_COLUMNS",
    "PENDING_ORDER_COLUMNS",
    "REWARD_COLUMNS",
    "TRADE_COLUMNS",
    "TradeJournal",
    "TradeJournalPaths",
]
