"""Simulation API request and result schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SimulationRequest(BaseModel):
    """HTTP request payload for ``SimulationParameters``.

    Every field is optional so callers can submit only the parameters they want
    to override from the backend defaults.  Validation is finalized by
    ``SimulationParameters.from_mapping`` so the API, runner, and strategy
    metadata share one canonical ruleset.
    """

    model_config = ConfigDict(extra="ignore")

    symbol: str | None = None
    timeframe: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    alpha_vantage_api_key: str | None = None
    broker_selection: str | None = None
    broker_api_key: str | None = None
    output_dir: str | None = None
    sequence_length: int | None = None
    generated_steps: int | None = None
    lstm_epochs: int | None = None
    lstm_batch_size: int | None = None
    lstm_learning_rate: float | None = None
    lstm_units_1: int | None = None
    lstm_units_2: int | None = None
    train_lstm: bool | None = None
    rl_algorithm: str | None = None
    rl_total_timesteps: int | None = None
    algo_hyperparams: dict[str, Any] | None = None
    rl_policy: str | None = None
    rl_model_name: str | None = None
    rl_verbose: int | None = None
    rl_device: str | None = None
    train_rl: bool | None = None
    evaluate_deterministic: bool | None = None
    initial_balance: float | None = None
    grid_levels: int | None = None
    grid_step_pct: float | None = None
    martingale_factor: float | None = None
    max_total_exposure: float | None = None
    grid_tp_multiplier: float | None = None
    grid_sl_multiplier: float | None = None
    base_position_size: float | None = None
    volatility_inverse_factor: float | None = None
    drawdown_penalty_percentage: float | None = None
    drawdown_high_watermark_bonus: float | None = None
    transaction_cost_pct: float | None = None
    time_decay_threshold_steps: int | None = None
    time_decay_penalty_per_step: float | None = None
    profit_threshold_for_decay: float | None = None
    early_exit_lookahead_steps: int | None = None
    early_exit_reward_factor: float | None = None
    early_exit_pnl_threshold_pct: float | None = None
    adaptive_averaging_enabled: bool | None = None
    averaging_trigger_pct: float | None = None
    max_averaging_levels: int | None = None
    averaging_step_pct: float | None = None
    averaging_tp_sl_mode: str | None = None
    averaging_volatility_threshold_atr: float | None = None
    max_averaging_drawdown_pct: float | None = None
    dynamic_martingale_rsi_extreme_threshold: int | None = None
    dynamic_martingale_macd_neutral_threshold: float | None = None
    averaging_tp_improvement_factor: float | None = None
    averaging_bonus_factor: float | None = None
    averaging_penalty_factor: float | None = None
    atr_filter_threshold: float | None = None
    bb_width_filter_threshold: float | None = None
    macd_signal_coincide_threshold: float | None = None
    rsi_oversold_bonus_threshold: int | None = None
    rsi_overbought_bonus_threshold: int | None = None
    macd_strong_trend_threshold: float | None = None
    rsi_extreme_threshold: int | None = None
    macd_cross_threshold: float | None = None
    save_charts: bool | None = None
    random_seed: int | None = None


class SimulationResultSchema(BaseModel):
    """HTTP representation of ``SimulationResult`` from the runner."""

    output_dir: str
    historical_data_path: str
    generated_data_path: str
    orders_path: str
    trades_path: str
    performance_path: str
    rewards_path: str
    equity_curve_path: str
    drawdown_path: str
    model_path: str | None = None
    equity_chart_path: str | None = None
    drawdown_chart_path: str | None = None
    performance: dict[str, Any] = Field(default_factory=dict)
    total_steps: int
    trained_lstm: bool
    trained_rl: bool


class SimulationArtifact(BaseModel):
    """One persisted file emitted by a simulation run."""

    name: str
    path: str
    exists: bool
    size_bytes: int | None = None


SimulationStatus = Literal["running", "completed", "failed"]


class SimulationRun(BaseModel):
    """Stored status document for a simulation request."""

    id: str
    status: SimulationStatus
    created_at: datetime
    completed_at: datetime | None = None
    parameters: dict[str, Any]
    result: SimulationResultSchema | None = None
    error: str | None = None


__all__ = [
    "SimulationArtifact",
    "SimulationRequest",
    "SimulationResultSchema",
    "SimulationRun",
    "SimulationStatus",
]
