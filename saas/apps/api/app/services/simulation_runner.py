"""End-to-end experiment runner for ADC pivot-grid simulations.

The runner turns the original notebook/README workflow into a reusable backend
service: it collects typed parameters, loads OHLCV data, calculates technical
indicators, optionally trains an LSTM generator, trains/evaluates a Stable
Baselines RL agent, and persists datasets, models, journals, metrics, and
charts under a single output directory.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

import numpy as np
import pandas as pd

from app.services.data_loader import DataLoader
from app.services.order_management import MockBrokerAPI, OrderManager
from app.services.pivot_env import PivotEnv
from app.services.rl_trainer import RLTrainer
from app.services.strategy_settings import SimulationParameters
from app.services.trade_journal import TradeJournal
from core.indicators import TechnicalIndicators
from core.lstm_model import LSTMPriceGenerator

logger = logging.getLogger(__name__)

LSTM_FEATURES = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "RSI",
    "MACD",
    "MACD_Signal",
    "RSI_Cross_Count",
    "Bb_Middle",
    "Bb_Upper",
    "Bb_Lower",
    "ATR",
]

ACTION_LABELS = {
    0: "None",
    1: "Buy Stop",
    2: "Sell Stop",
    3: "Buy Market",
    4: "Sell Market",
}


@dataclass(slots=True)
class SimulationResult:
    """Summary and file locations produced by a simulation run."""

    output_dir: str
    historical_data_path: str
    generated_data_path: str
    orders_path: str
    trades_path: str
    performance_path: str
    rewards_path: str
    equity_curve_path: str
    drawdown_path: str
    model_path: Optional[str]
    equity_chart_path: Optional[str]
    drawdown_chart_path: Optional[str]
    performance: dict[str, Any]
    total_steps: int
    trained_lstm: bool
    trained_rl: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        return asdict(self)


class SimulationRunner:
    """Coordinate data loading, feature engineering, ML training, and outputs."""

    def __init__(
        self,
        data_loader: Optional[DataLoader] = None,
        broker_api: Optional[MockBrokerAPI] = None,
        order_manager: Optional[OrderManager] = None,
        logger_fn: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.data_loader = data_loader
        self.broker_api = broker_api or MockBrokerAPI(trade_allowed=True)
        self.order_manager = order_manager or OrderManager(self.broker_api)
        self.logger_fn = logger_fn

    def run(self, params: SimulationParameters | Mapping[str, Any] | None = None) -> SimulationResult:
        """Run the full simulation pipeline and persist all artifacts."""

        config = params if isinstance(params, SimulationParameters) else SimulationParameters.from_mapping(params)
        if config.random_seed is not None:
            np.random.seed(config.random_seed)

        self._log(f"Starting simulation for {config.symbol} ({config.timeframe}).")
        output_dir = config.ensure_output_dir()
        trade_journal = TradeJournal(output_dir)
        journal_paths = trade_journal.ensure_directories()

        loader = self.data_loader or DataLoader(config.alpha_vantage_api_key)
        raw_data = loader.fetch_data(
            config.symbol,
            timeframe=config.timeframe,
            start_date=config.start_date,
            end_date=config.end_date,
        )
        historical_df = self._prepare_historical_data(raw_data)
        generated_df, lstm_metadata = self._generate_lstm_data(historical_df, config)
        historical_df, generated_df = self._align_frames(historical_df, generated_df)

        historical_data_path = output_dir / "historical_df.csv"
        generated_data_path = output_dir / "generated_df.csv"
        historical_df.to_csv(historical_data_path, index=True)
        generated_df.to_csv(generated_data_path, index=True)

        model, model_path = self._train_rl_agent(historical_df, generated_df, config, output_dir)
        evaluation = self._evaluate_policy(historical_df, generated_df, config, model)

        performance = trade_journal.calculate_performance(evaluation["trades"], evaluation["equity_curve"])
        performance.update(
            {
                "symbol": config.symbol,
                "timeframe": config.timeframe,
                "rl_algorithm": config.rl_algorithm.upper(),
                "trained_lstm": lstm_metadata["trained_lstm"],
                "trained_rl": model is not None,
            }
        )
        trade_journal.save_report(
            trades=evaluation["trades"],
            pending_orders=evaluation["pending_orders"],
            equity_curve=evaluation["equity_curve"],
            drawdown=evaluation["drawdown"],
            rewards=evaluation["rewards"],
            performance=performance,
            actions=evaluation["orders"],
        )

        equity_chart_path = None
        drawdown_chart_path = None
        if config.save_charts:
            equity_chart_path, drawdown_chart_path = self._save_charts(
                evaluation["equity_curve"], evaluation["drawdown"], journal_paths
            )

        self._log("Simulation complete; artifacts saved.")
        return SimulationResult(
            output_dir=str(output_dir),
            historical_data_path=str(historical_data_path),
            generated_data_path=str(generated_data_path),
            orders_path=str(journal_paths.pending_orders_path),
            trades_path=str(journal_paths.trades_path),
            performance_path=str(journal_paths.performance_path),
            rewards_path=str(journal_paths.rewards_path),
            equity_curve_path=str(journal_paths.equity_curve_path),
            drawdown_path=str(journal_paths.drawdown_path),
            model_path=str(model_path) if model_path else None,
            equity_chart_path=str(equity_chart_path) if equity_chart_path else None,
            drawdown_chart_path=str(drawdown_chart_path) if drawdown_chart_path else None,
            performance=performance,
            total_steps=evaluation["total_steps"],
            trained_lstm=lstm_metadata["trained_lstm"],
            trained_rl=model is not None,
        )

    def _prepare_historical_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        if raw_data.empty:
            raise ValueError("No data fetched for the requested symbol/timeframe.")

        data = raw_data.copy()
        data.columns = [str(column).strip().capitalize() for column in data.columns]
        if "Adj close" in data.columns and "Close" not in data.columns:
            data = data.rename(columns={"Adj close": "Close"})
        if not DataLoader.validate_ohlcv(data):
            raise ValueError("Input data must contain Open, High, Low, Close, and Volume columns.")

        data = TechnicalIndicators.add_all_indicators(data)
        data["RSI_Cross_Count"] = TechnicalIndicators.count_rsi_crosses(data["RSI"])
        data = data.replace([np.inf, -np.inf], np.nan).dropna()
        if len(data) < 2:
            raise ValueError("Not enough rows after indicator calculation.")
        return data

    def _generate_lstm_data(
        self, historical_df: pd.DataFrame, config: SimulationParameters
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        features = [feature for feature in LSTM_FEATURES if feature in historical_df.columns]
        missing = sorted(set(LSTM_FEATURES) - set(features))
        if missing:
            raise ValueError(f"Missing required LSTM features: {missing}")

        generated_steps = config.generated_steps or len(historical_df)
        fallback_df = self._fallback_generated_data(historical_df, features, generated_steps)
        if not config.train_lstm:
            return fallback_df, {"trained_lstm": False, "reason": "disabled"}

        generator = LSTMPriceGenerator()
        train_result = generator.train(
            historical_df,
            features=features,
            sequence_length=config.sequence_length,
            lstm_units_1=config.lstm_units_1,
            lstm_units_2=config.lstm_units_2,
            learning_rate=config.lstm_learning_rate,
            epochs=config.lstm_epochs,
            batch_size=config.lstm_batch_size,
            validation_split=0.2,
            verbose=0,
        )
        if not train_result.get("success"):
            self._log("LSTM training skipped; using historical feature fallback as generated data.")
            return fallback_df, {"trained_lstm": False, "reason": train_result.get("message")}

        X, _, _ = generator.prepare_sequences(historical_df, features, config.sequence_length)
        if len(X) == 0:
            return fallback_df, {"trained_lstm": False, "reason": "no seed sequence"}

        generated_df = generator.generate(X[-1], num_steps=generated_steps, features_list=features)
        generated_df = self._normalize_generated_ohlc(generated_df)
        generated_df = self._complete_generated_indicators(generated_df)
        return generated_df, {"trained_lstm": True, "reason": "trained"}

    def _fallback_generated_data(
        self, historical_df: pd.DataFrame, features: list[str], generated_steps: int
    ) -> pd.DataFrame:
        generated = historical_df[features].tail(generated_steps).copy().reset_index(drop=True)
        return self._complete_generated_indicators(generated)

    def _normalize_generated_ohlc(self, generated_df: pd.DataFrame) -> pd.DataFrame:
        generated = generated_df.copy()
        for column in ["Open", "High", "Low", "Close"]:
            if column in generated.columns:
                generated[column] = generated[column].astype(float).round(5)
        if {"Open", "High", "Low", "Close"}.issubset(generated.columns):
            high_floor = generated[["Open", "Close", "High"]].max(axis=1)
            low_ceiling = generated[["Open", "Close", "Low"]].min(axis=1)
            generated["High"] = high_floor
            generated["Low"] = low_ceiling
        return generated

    def _complete_generated_indicators(self, generated_df: pd.DataFrame) -> pd.DataFrame:
        generated = generated_df.copy()
        if {"Open", "High", "Low", "Close"}.issubset(generated.columns):
            generated = TechnicalIndicators.calculate_pivots(generated)
        for column in ["RSI", "MACD", "MACD_Signal", "Bb_Middle", "Bb_Upper", "Bb_Lower", "ATR"]:
            if column not in generated.columns:
                generated[column] = 0.0
        if "RSI_Cross_Count" not in generated.columns:
            generated["RSI_Cross_Count"] = TechnicalIndicators.count_rsi_crosses(generated["RSI"])
        return generated.replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0.0)

    def _align_frames(
        self, historical_df: pd.DataFrame, generated_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        min_length = min(len(historical_df), len(generated_df))
        if min_length < 2:
            raise ValueError("Not enough aligned historical/generated rows for RL training.")
        return historical_df.iloc[:min_length].copy(), generated_df.iloc[:min_length].copy()

    def _make_env(self, historical_df: pd.DataFrame, generated_df: pd.DataFrame, config: SimulationParameters) -> PivotEnv:
        return PivotEnv(
            historical_df,
            generated_df,
            self.broker_api,
            self.order_manager,
            **config.env_kwargs(),
        )

    def _train_rl_agent(
        self,
        historical_df: pd.DataFrame,
        generated_df: pd.DataFrame,
        config: SimulationParameters,
        output_dir: Path,
    ) -> tuple[Any | None, Path | None]:
        if not config.train_rl:
            return None, None

        training_config = config.to_rl_training_config()
        trainer = RLTrainer(
            env_factory=lambda: self._make_env(historical_df, generated_df, config),
            output_dir=output_dir,
        )
        result = trainer.train(training_config)
        return result.model, result.model_path

    def _evaluate_policy(
        self,
        historical_df: pd.DataFrame,
        generated_df: pd.DataFrame,
        config: SimulationParameters,
        model: Any | None,
    ) -> dict[str, Any]:
        env = self._make_env(historical_df, generated_df, config)
        obs, _ = env.reset(seed=config.random_seed)
        records: list[dict[str, Any]] = []
        reward_records: list[dict[str, Any]] = []

        while True:
            current_step = env.current_step
            if model is None:
                action = 0
            else:
                prediction, _ = model.predict(obs, deterministic=config.evaluate_deterministic)
                action = int(np.asarray(prediction).item())

            if current_step < len(historical_df):
                row = historical_df.iloc[current_step]
                records.append(
                    {
                        "Index": historical_df.index[current_step],
                        "Action": ACTION_LABELS.get(action, "Unknown"),
                        "Action_Id": action,
                        "Price": float(row["Close"]),
                        "RSI": float(row["RSI"]),
                        "MACD": float(row["MACD"]),
                        "MACD_Signal": float(row["MACD_Signal"]),
                    }
                )

            obs, reward, done, _, _ = env.step(action)
            reward_records.append({"Step": current_step, "Reward": float(reward)})
            if done:
                break

        trades = pd.DataFrame(env.closed_trades)
        pending_orders = pd.DataFrame(env.pending_orders)
        orders = pd.DataFrame(records)
        rewards = pd.DataFrame(reward_records)
        equity_curve = pd.Series(env.equity_history, dtype="float64")
        drawdown = self._reporting_journal().calculate_drawdown(equity_curve)
        return {
            "orders": orders,
            "pending_orders": pending_orders,
            "trades": trades,
            "rewards": rewards,
            "equity_curve": equity_curve,
            "drawdown": drawdown,
            "total_steps": len(reward_records),
        }


    def _reporting_journal(self) -> TradeJournal:
        """Return an in-memory journal helper for calculations only."""

        return TradeJournal(".")

    def _save_charts(
        self, equity_curve: pd.Series, drawdown: pd.Series, journal_paths: Any
    ) -> tuple[Path | None, Path | None]:
        if equity_curve.empty:
            return None, None
        pyplot = import_module("matplotlib.pyplot")
        equity_path = journal_paths.equity_chart_path
        drawdown_path = journal_paths.drawdown_chart_path

        pyplot.figure(figsize=(12, 6))
        equity_curve.plot(title="Equity Curve")
        pyplot.xlabel("Step")
        pyplot.ylabel("Balance")
        pyplot.tight_layout()
        pyplot.savefig(equity_path)
        pyplot.close()

        pyplot.figure(figsize=(12, 6))
        drawdown.plot(title="Drawdown")
        pyplot.xlabel("Step")
        pyplot.ylabel("Drawdown (%)")
        pyplot.tight_layout()
        pyplot.savefig(drawdown_path)
        pyplot.close()
        return equity_path, drawdown_path

    def _log(self, message: str) -> None:
        logger.info(message)
        if self.logger_fn:
            self.logger_fn(message)


def run_simulation(params: SimulationParameters | Mapping[str, Any] | None = None) -> SimulationResult:
    """Convenience wrapper for one-shot simulation runs."""

    return SimulationRunner().run(params)


__all__ = ["SimulationParameters", "SimulationResult", "SimulationRunner", "run_simulation"]
