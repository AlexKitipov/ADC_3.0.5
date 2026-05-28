"""Typed strategy settings for backend simulations.

The notebook version of ADC collected strategy inputs from ``ipywidgets`` and
passed a loose dictionary around the simulation function.  This module is the
backend equivalent: it documents every supported parameter, accepts the legacy
widget/README aliases, coerces API payload values into Python types, validates
safe ranges/options, and exposes helpers that prepare the RL environment and
trainer configuration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Mapping, Optional, get_args, get_origin, get_type_hints

SUPPORTED_TIMEFRAMES = ("1d", "5min", "15min", "30min", "60min")
SUPPORTED_RL_ALGORITHMS = ("PPO", "DQN", "A2C", "SAC")
SUPPORTED_AVERAGING_TP_SL_MODES = ("consolidated", "individual")
SUPPORTED_BROKERS = (
    "None",
    "Interactive Brokers",
    "IG Markets",
    "CMC Markets",
    "Tradier",
    "Capital.com",
    "FOREX.com",
    "Dukascopy",
    "Binance",
    "Bybit",
    "Kraken",
    "MetaTrader 5",
    "QuantConnect",
    "Tastytrade",
    "Zacks Trade",
    "Optimus Futures",
)

README_PARAMETER_ALIASES = {
    "alpha_key": "alpha_vantage_api_key",
    "base_path": "output_dir",
    "balance": "initial_balance",
    "ppo_total_timesteps": "rl_total_timesteps",
    "rl_hyperparameters": "algo_hyperparams",
}

ENV_PARAMETER_NAMES = (
    "initial_balance",
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
)


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """Backend description of a notebook widget parameter."""

    name: str
    group: str
    label: str
    default: Any
    min_value: float | int | None = None
    max_value: float | int | None = None
    step: float | int | None = None
    options: tuple[Any, ...] = ()
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for API metadata."""

        payload = asdict(self)
        payload["options"] = list(self.options)
        return payload


@dataclass(slots=True)
class SimulationParameters:
    """Validated typed configuration for one ADC strategy simulation run."""

    symbol: str = "TSLA"
    timeframe: str = "1d"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    broker_selection: str = "None"
    broker_api_key: Optional[str] = None
    output_dir: str = "simulation_output"

    sequence_length: int = 20
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

    initial_balance: float = 10_000.0
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

    def __post_init__(self) -> None:
        self.rl_algorithm = self.rl_algorithm.upper()
        self._validate()

    @classmethod
    def defaults_for_dates(cls, today: date | None = None) -> tuple[str, str]:
        """Return the README's default two-year date window."""

        current_day = today or date.today()
        return (current_day - timedelta(days=365 * 2)).isoformat(), current_day.isoformat()

    @classmethod
    def from_mapping(cls, params: Mapping[str, Any] | None = None) -> "SimulationParameters":
        """Build parameters from an API/UI dict, ignoring unknown widget-only keys."""

        if params is None:
            return cls()

        type_hints = get_type_hints(cls)
        field_types = {item.name: type_hints[item.name] for item in fields(cls)}
        normalized: dict[str, Any] = {}
        for key, value in params.items():
            target = README_PARAMETER_ALIASES.get(key, key)
            if target in field_types:
                normalized[target] = _coerce_value(value, field_types[target], target)
        return cls(**normalized)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly strategy configuration."""

        return asdict(self)

    def env_kwargs(self) -> dict[str, Any]:
        """Return the subset consumed by ``PivotEnv``."""

        return {name: getattr(self, name) for name in ENV_PARAMETER_NAMES}

    def to_rl_training_config(self) -> "RLTrainingConfig":
        """Prepare a typed Stable-Baselines trainer config from strategy settings."""

        from app.services.rl_trainer import RLTrainingConfig

        return RLTrainingConfig(
            algorithm=self.rl_algorithm,
            total_timesteps=self.rl_total_timesteps,
            hyperparameters=self.algo_hyperparams,
            policy=self.rl_policy,
            model_name=self.rl_model_name,
            seed=self.random_seed,
            verbose=self.rl_verbose,
            device=self.rl_device,
        )

    def ensure_output_dir(self) -> Path:
        """Create and return the configured output directory."""

        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    def _validate(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty.")
        _validate_option("timeframe", self.timeframe, SUPPORTED_TIMEFRAMES)
        _validate_option("broker_selection", self.broker_selection, SUPPORTED_BROKERS)
        _validate_option("rl_algorithm", self.rl_algorithm.upper(), SUPPORTED_RL_ALGORITHMS)
        _validate_option("averaging_tp_sl_mode", self.averaging_tp_sl_mode, SUPPORTED_AVERAGING_TP_SL_MODES)
        _validate_date_order(self.start_date, self.end_date)
        if self.generated_steps is not None:
            _validate_range("generated_steps", self.generated_steps, min_value=1)
        for spec in PARAMETER_SPECS.values():
            if spec.name in {"symbol", "start_date", "end_date", "alpha_vantage_api_key", "broker_api_key"}:
                continue
            value = getattr(self, spec.name, None)
            if spec.options:
                _validate_option(spec.name, value, spec.options)
            if spec.min_value is not None or spec.max_value is not None:
                _validate_range(spec.name, value, spec.min_value, spec.max_value)
        if not isinstance(self.algo_hyperparams, dict):
            raise TypeError("algo_hyperparams must be a dictionary.")


PARAMETER_SPECS: dict[str, ParameterSpec] = {
    "symbol": ParameterSpec("symbol", "data", "Symbol", "TSLA", description="Market symbol/ticker to simulate."),
    "timeframe": ParameterSpec("timeframe", "data", "Timeframe", "1d", options=SUPPORTED_TIMEFRAMES),
    "start_date": ParameterSpec("start_date", "data", "Start Date", None),
    "end_date": ParameterSpec("end_date", "data", "End Date", None),
    "alpha_vantage_api_key": ParameterSpec("alpha_vantage_api_key", "data", "AV API Key", None),
    "broker_selection": ParameterSpec("broker_selection", "data", "Broker", "None", options=SUPPORTED_BROKERS),
    "broker_api_key": ParameterSpec("broker_api_key", "data", "Broker API Key", None),
    "sequence_length": ParameterSpec("sequence_length", "lstm", "Seq Length", 20, 5, 100, 5),
    "lstm_epochs": ParameterSpec("lstm_epochs", "lstm", "LSTM Epochs", 50, 10, 100, 10),
    "lstm_batch_size": ParameterSpec("lstm_batch_size", "lstm", "LSTM Batch Size", 64, 16, 128, 16),
    "lstm_learning_rate": ParameterSpec("lstm_learning_rate", "lstm", "LSTM LR", 0.001, 0.0001, 0.01, 0.0001),
    "lstm_units_1": ParameterSpec("lstm_units_1", "lstm", "LSTM Units 1", 64, 16, 128, 16),
    "lstm_units_2": ParameterSpec("lstm_units_2", "lstm", "LSTM Units 2", 32, 16, 128, 16),
    "rl_total_timesteps": ParameterSpec("rl_total_timesteps", "rl", "RL Total Timesteps", 50_000, 1, 500_000, 10_000),
    "rl_algorithm": ParameterSpec("rl_algorithm", "rl", "RL Algorithm", "PPO", options=SUPPORTED_RL_ALGORITHMS),
    "initial_balance": ParameterSpec("initial_balance", "pivot", "Balance", 10_000.0, 1_000.0, 100_000.0, 1_000.0),
    "base_position_size": ParameterSpec("base_position_size", "pivot", "Base Pos Size", 1.0, 0.01, 10.0, 0.01),
    "volatility_inverse_factor": ParameterSpec("volatility_inverse_factor", "pivot", "Vol Inv Factor", 0.01, 0.0, 0.1, 0.001),
    "drawdown_penalty_percentage": ParameterSpec("drawdown_penalty_percentage", "pivot", "DD Penalty %", 0.05, 0.01, 0.2, 0.01),
    "drawdown_high_watermark_bonus": ParameterSpec("drawdown_high_watermark_bonus", "pivot", "DD HW Bonus", 0.005, 0.001, 0.05, 0.001),
    "transaction_cost_pct": ParameterSpec("transaction_cost_pct", "pivot", "Tx Cost %", 0.0005, 0.0001, 0.001, 0.0001),
    "time_decay_threshold_steps": ParameterSpec("time_decay_threshold_steps", "pivot", "Time Decay Threshold", 5, 1, 20, 1),
    "time_decay_penalty_per_step": ParameterSpec("time_decay_penalty_per_step", "pivot", "Time Decay Penalty", -0.02, -0.1, 0.0, 0.01),
    "profit_threshold_for_decay": ParameterSpec("profit_threshold_for_decay", "pivot", "Profit Thresh Decay", 0.01, 0.0, 0.1, 0.005),
    "early_exit_lookahead_steps": ParameterSpec("early_exit_lookahead_steps", "pivot", "Early Exit Lookahead", 5, 1, 10, 1),
    "early_exit_reward_factor": ParameterSpec("early_exit_reward_factor", "pivot", "Early Exit Reward Factor", 0.5, 0.0, 1.0, 0.1),
    "early_exit_pnl_threshold_pct": ParameterSpec("early_exit_pnl_threshold_pct", "pivot", "Early Exit PnL Thresh %", 0.001, 0.0, 0.01, 0.0001),
    "grid_levels": ParameterSpec("grid_levels", "grid", "Grid Levels", 3, 1, 5, 1),
    "grid_step_pct": ParameterSpec("grid_step_pct", "grid", "Grid Step %", 0.005, 0.001, 0.01, 0.001),
    "martingale_factor": ParameterSpec("martingale_factor", "grid", "Martingale Factor", 1.1, 1.0, 2.0, 0.1),
    "max_total_exposure": ParameterSpec("max_total_exposure", "grid", "Max Total Exposure", 10.0, 1.0, 50.0, 1.0),
    "grid_tp_multiplier": ParameterSpec("grid_tp_multiplier", "grid", "Grid TP Multiplier", 1.5, 0.5, 3.0, 0.1),
    "grid_sl_multiplier": ParameterSpec("grid_sl_multiplier", "grid", "Grid SL Multiplier", 1.0, 0.5, 3.0, 0.1),
    "averaging_trigger_pct": ParameterSpec("averaging_trigger_pct", "averaging", "Avg Trigger %", 0.01, 0.001, 0.05, 0.001),
    "max_averaging_levels": ParameterSpec("max_averaging_levels", "averaging", "Max Avg Levels", 2, 0, 5, 1),
    "averaging_step_pct": ParameterSpec("averaging_step_pct", "averaging", "Avg Step %", 0.005, 0.001, 0.02, 0.001),
    "averaging_tp_sl_mode": ParameterSpec("averaging_tp_sl_mode", "averaging", "Avg TP/SL Mode", "consolidated", options=SUPPORTED_AVERAGING_TP_SL_MODES),
    "averaging_volatility_threshold_atr": ParameterSpec("averaging_volatility_threshold_atr", "averaging", "Avg Vol Threshold ATR", 0.5, 0.1, 2.0, 0.1),
    "max_averaging_drawdown_pct": ParameterSpec("max_averaging_drawdown_pct", "averaging", "Max Avg DD %", 0.05, 0.01, 0.1, 0.01),
    "dynamic_martingale_rsi_extreme_threshold": ParameterSpec("dynamic_martingale_rsi_extreme_threshold", "averaging", "Dyn Martingale RSI Ext Thresh", 20, 10, 40, 5),
    "dynamic_martingale_macd_neutral_threshold": ParameterSpec("dynamic_martingale_macd_neutral_threshold", "averaging", "Dyn Martingale MACD Neut Thresh", 0.01, 0.0, 0.05, 0.001),
    "averaging_tp_improvement_factor": ParameterSpec("averaging_tp_improvement_factor", "averaging", "Avg TP Improve Factor", 0.001, 0.0, 0.01, 0.0001),
    "averaging_bonus_factor": ParameterSpec("averaging_bonus_factor", "averaging", "Avg Bonus Factor", 0.1, 0.0, 0.5, 0.01),
    "averaging_penalty_factor": ParameterSpec("averaging_penalty_factor", "averaging", "Avg Penalty Factor", -0.05, -0.2, 0.0, 0.01),
    "atr_filter_threshold": ParameterSpec("atr_filter_threshold", "filters", "ATR Filter Thresh", 0.0, 0.0, 1.0, 0.01),
    "bb_width_filter_threshold": ParameterSpec("bb_width_filter_threshold", "filters", "BB Width Filter Thresh", 0.0, 0.0, 20.0, 0.1),
    "macd_signal_coincide_threshold": ParameterSpec("macd_signal_coincide_threshold", "filters", "MACD Signal Coincide Thresh", 0.0, 0.0, 0.1, 0.005),
    "rsi_oversold_bonus_threshold": ParameterSpec("rsi_oversold_bonus_threshold", "filters", "RSI Oversold Thresh", 30, 10, 40, 1),
    "rsi_overbought_bonus_threshold": ParameterSpec("rsi_overbought_bonus_threshold", "filters", "RSI Overbought Thresh", 70, 60, 90, 1),
    "macd_strong_trend_threshold": ParameterSpec("macd_strong_trend_threshold", "filters", "MACD Strong Trend Thresh", 0.0, 0.0, 0.2, 0.01),
    "rsi_extreme_threshold": ParameterSpec("rsi_extreme_threshold", "filters", "RSI Extreme Thresh", 0, 0, 30, 1),
    "macd_cross_threshold": ParameterSpec("macd_cross_threshold", "filters", "MACD Cross Thresh", 0.0, 0.0, 0.1, 0.01),
}


def strategy_parameter_specs() -> list[dict[str, Any]]:
    """Return parameter metadata grouped from the original Colab widgets."""

    return [spec.to_dict() for spec in PARAMETER_SPECS.values()]


def _coerce_value(value: Any, annotation: Any, field_name: str) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        return value
    if origin in {dict, Mapping}:
        if not isinstance(value, Mapping):
            raise TypeError(f"{field_name} must be a mapping.")
        return dict(value)
    if type(None) in args:
        non_none = next(arg for arg in args if arg is not type(None))
        if value is None or value == "":
            return None
        return _coerce_value(value, non_none, field_name)
    if annotation is bool:
        return _coerce_bool(value, field_name)
    if annotation is int:
        if isinstance(value, bool):
            raise TypeError(f"{field_name} must be an integer, not a boolean.")
        return int(value)
    if annotation is float:
        if isinstance(value, bool):
            raise TypeError(f"{field_name} must be a float, not a boolean.")
        return float(value)
    if annotation is str:
        return str(value)
    return value


def _coerce_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise TypeError(f"{field_name} must be a boolean.")


def _validate_option(name: str, value: Any, options: tuple[Any, ...]) -> None:
    if value not in options:
        choices = ", ".join(str(option) for option in options)
        raise ValueError(f"{name} must be one of: {choices}.")


def _validate_range(
    name: str,
    value: Any,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric.")
    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be >= {min_value}.")
    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be <= {max_value}.")


def _validate_date_order(start_date: str | None, end_date: str | None) -> None:
    if not start_date or not end_date:
        return
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    if start > end:
        raise ValueError("start_date must be before or equal to end_date.")


__all__ = [
    "ENV_PARAMETER_NAMES",
    "PARAMETER_SPECS",
    "README_PARAMETER_ALIASES",
    "SUPPORTED_AVERAGING_TP_SL_MODES",
    "SUPPORTED_BROKERS",
    "SUPPORTED_RL_ALGORITHMS",
    "SUPPORTED_TIMEFRAMES",
    "ParameterSpec",
    "SimulationParameters",
    "strategy_parameter_specs",
]
