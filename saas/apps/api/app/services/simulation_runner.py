"""End-to-end experiment runner for ADC pivot-grid simulations.

The runner turns the original notebook/README workflow into a reusable backend
service: it collects typed parameters, loads OHLCV data, calculates technical
indicators, optionally trains an LSTM generator, trains/evaluates a Stable
Baselines RL agent, and persists datasets, models, journals, metrics, and
charts under a single output directory.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

import numpy as np
import pandas as pd

from app.services.data_loader import DataLoader
from app.services.order_management import MockBrokerAPI, OrderManager
from app.services.pivot_env import PivotEnv
from app.services.rl_trainer import RLTrainer, RLTrainingConfig
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
class SimulationParameters:
    """All tunable inputs for one simulation run.

    Defaults mirror the notebook controls where practical, while adding flags
    that make automated tests and quick smoke runs possible without heavy ML
    training.
    """

    symbol: str = "TSLA"
    timeframe: str = "1d"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    output_dir: str = "simulation_output"

    sequence_length: int = 60
    generated_steps: Optional[int] = None
    lstm_epochs: int = 50
    lstm_batch_size: int = 64
    lstm_learning_rate: float = 0.001
    lstm_units_1: int = 64
    lstm_units_2: int = 32
    train_lstm: bool = True

    rl_algorithm: str = "PPO"
    rl_total_timesteps: int = 50_000
    algo_hyperparams: dict[str, Any] = field(default_factory=dict)
    rl_policy: str = "MlpPolicy"
    rl_model_name: Optional[str] = None
    rl_verbose: int = 0
    rl_device: str = "auto"
    train_rl: bool = True
    evaluate_deterministic: bool = True

    grid_levels: int = 3
    grid_step_pct: float = 0.005
    martingale_factor: float = 1.1
    max_total_exposure: float = 10.0
    grid_tp_multiplier: float = 1.5
    grid_sl_multiplier: float = 1.0
    base_position_size: float = 1.0
    volatility_inverse_factor: float = 0.01
    drawdown_penalty_percentage: float = 0.05
    drawdown_high_watermark_bonus: float = 0.005
    transaction_cost_pct: float = 0.0005
    time_decay_threshold_steps: int = 5
    time_decay_penalty_per_step: float = -0.02
    profit_threshold_for_decay: float = 0.01
    early_exit_lookahead_steps: int = 5
    early_exit_reward_factor: float = 0.5
    early_exit_pnl_threshold_pct: float = 0.001
    adaptive_averaging_enabled: bool = False
    averaging_trigger_pct: float = 0.01
    max_averaging_levels: int = 2
    averaging_step_pct: float = 0.005
    averaging_tp_sl_mode: str = "consolidated"
    averaging_volatility_threshold_atr: float = 0.5
    max_averaging_drawdown_pct: float = 0.05
    dynamic_martingale_rsi_extreme_threshold: int = 20
    dynamic_martingale_macd_neutral_threshold: float = 0.01
    averaging_tp_improvement_factor: float = 0.001
    averaging_bonus_factor: float = 0.1
    averaging_penalty_factor: float = -0.05
    atr_filter_threshold: float = 0.0
    bb_width_filter_threshold: float = 0.0
    macd_signal_coincide_threshold: float = 0.0
    rsi_oversold_bonus_threshold: int = 30
    rsi_overbought_bonus_threshold: int = 70
    macd_strong_trend_threshold: float = 0.0
    rsi_extreme_threshold: int = 0
    macd_cross_threshold: float = 0.0

    save_charts: bool = True
    random_seed: Optional[int] = None

    @classmethod
    def from_mapping(cls, params: Mapping[str, Any] | None = None) -> "SimulationParameters":
        """Build parameters from a dict, ignoring unknown UI-only keys."""

        if params is None:
            return cls()

        aliases = {
            "ppo_total_timesteps": "rl_total_timesteps",
            "alpha_key": "alpha_vantage_api_key",
            "base_path": "output_dir",
        }
        fields = cls.__dataclass_fields__
        normalized: dict[str, Any] = {}
        for key, value in params.items():
            target = aliases.get(key, key)
            if target in fields:
                normalized[target] = value
        return cls(**normalized)


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
        output_dir = Path(config.output_dir)
        journal_dir = output_dir / "TradeJournal"
        charts_dir = journal_dir / "charts"
        output_dir.mkdir(parents=True, exist_ok=True)
        journal_dir.mkdir(parents=True, exist_ok=True)
        charts_dir.mkdir(parents=True, exist_ok=True)

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

        orders_path = output_dir / "pending_orders_v2.csv"
        trades_path = journal_dir / "trades_v2.csv"
        rewards_path = journal_dir / "rewards_v2.csv"
        performance_path = journal_dir / "performance_v2.json"

        evaluation["orders"].to_csv(orders_path, index=False)
        evaluation["trades"].to_csv(trades_path, index=False)
        evaluation["rewards"].to_csv(rewards_path, index=False)

        performance = self._calculate_performance(evaluation["trades"], evaluation["equity_curve"])
        performance.update(
            {
                "symbol": config.symbol,
                "timeframe": config.timeframe,
                "rl_algorithm": config.rl_algorithm.upper(),
                "trained_lstm": lstm_metadata["trained_lstm"],
                "trained_rl": model is not None,
            }
        )
        performance_path.write_text(json.dumps(performance, indent=2), encoding="utf-8")

        equity_chart_path = None
        drawdown_chart_path = None
        if config.save_charts:
            equity_chart_path, drawdown_chart_path = self._save_charts(
                evaluation["equity_curve"], evaluation["drawdown"], charts_dir
            )

        self._log("Simulation complete; artifacts saved.")
        return SimulationResult(
            output_dir=str(output_dir),
            historical_data_path=str(historical_data_path),
            generated_data_path=str(generated_data_path),
            orders_path=str(orders_path),
            trades_path=str(trades_path),
            performance_path=str(performance_path),
            rewards_path=str(rewards_path),
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
        env_kwargs = {
            key: getattr(config, key)
            for key in [
                "grid_levels",
                "grid_step_pct",
                "martingale_factor",
                "max_total_exposure",
                "grid_tp_multiplier",
                "grid_sl_multiplier",
                "base_position_size",
                "volatility_inverse_factor",
                "drawdown_penalty_percentage",
                "drawdown_high_watermark_bonus",
                "transaction_cost_pct",
                "time_decay_threshold_steps",
                "time_decay_penalty_per_step",
                "profit_threshold_for_decay",
                "early_exit_lookahead_steps",
                "early_exit_reward_factor",
                "early_exit_pnl_threshold_pct",
                "adaptive_averaging_enabled",
                "averaging_trigger_pct",
                "max_averaging_levels",
                "averaging_step_pct",
                "averaging_tp_sl_mode",
                "averaging_volatility_threshold_atr",
                "max_averaging_drawdown_pct",
                "dynamic_martingale_rsi_extreme_threshold",
                "dynamic_martingale_macd_neutral_threshold",
                "averaging_tp_improvement_factor",
                "averaging_bonus_factor",
                "averaging_penalty_factor",
                "atr_filter_threshold",
                "bb_width_filter_threshold",
                "macd_signal_coincide_threshold",
                "rsi_oversold_bonus_threshold",
                "rsi_overbought_bonus_threshold",
                "macd_strong_trend_threshold",
                "rsi_extreme_threshold",
                "macd_cross_threshold",
            ]
        }
        return PivotEnv(historical_df, generated_df, self.broker_api, self.order_manager, **env_kwargs)

    def _train_rl_agent(
        self,
        historical_df: pd.DataFrame,
        generated_df: pd.DataFrame,
        config: SimulationParameters,
        output_dir: Path,
    ) -> tuple[Any | None, Path | None]:
        if not config.train_rl:
            return None, None

        training_config = RLTrainingConfig(
            algorithm=config.rl_algorithm,
            total_timesteps=config.rl_total_timesteps,
            hyperparameters=config.algo_hyperparams,
            policy=config.rl_policy,
            model_name=config.rl_model_name,
            seed=config.random_seed,
            verbose=config.rl_verbose,
            device=config.rl_device,
        )
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
        orders = pd.DataFrame(records)
        rewards = pd.DataFrame(reward_records)
        equity_curve = pd.Series(env.equity_history, dtype="float64")
        drawdown = self._calculate_drawdown(equity_curve)
        return {
            "orders": orders,
            "trades": trades,
            "rewards": rewards,
            "equity_curve": equity_curve,
            "drawdown": drawdown,
            "total_steps": len(reward_records),
        }

    def _calculate_performance(self, trades_df: pd.DataFrame, equity_curve: pd.Series) -> dict[str, Any]:
        drawdown = self._calculate_drawdown(equity_curve)
        max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
        performance: dict[str, Any] = {
            "total_trades": int(len(trades_df)),
            "max_drawdown": max_drawdown,
            "final_equity": float(equity_curve.iloc[-1]) if not equity_curve.empty else 0.0,
        }
        if trades_df.empty or "pnl" not in trades_df.columns:
            performance.update({"win_rate": 0.0, "avg_profit": 0.0, "avg_loss": 0.0, "expectancy": 0.0})
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

    def _calculate_drawdown(self, equity_curve: pd.Series) -> pd.Series:
        if equity_curve.empty:
            return pd.Series(dtype="float64")
        roll_max = equity_curve.cummax().replace(0, np.nan)
        return ((equity_curve - roll_max) / roll_max).fillna(0.0)

    def _save_charts(self, equity_curve: pd.Series, drawdown: pd.Series, charts_dir: Path) -> tuple[Path | None, Path | None]:
        if equity_curve.empty:
            return None, None
        pyplot = import_module("matplotlib.pyplot")
        equity_path = charts_dir / "equity_curve_v2.png"
        drawdown_path = charts_dir / "drawdown_v2.png"

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
