"""Reinforcement-learning training API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RLAlgorithm = Literal["PPO", "DQN", "A2C", "SAC"]
RLEnvironment = Literal["pivot-grid"]
RLTrainingStatus = Literal["running", "completed", "failed"]


class RLTrainingRequest(BaseModel):
    """Payload used to start a standalone RL training job."""

    model_config = ConfigDict(extra="ignore")

    algorithm: RLAlgorithm = "PPO"
    total_timesteps: int = Field(default=50_000, ge=1, le=500_000)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    policy: str = "MlpPolicy"
    model_name: str | None = None
    save_model: bool = True
    seed: int | None = None
    verbose: int = 0
    device: str = "auto"
    environment: RLEnvironment = "pivot-grid"

    symbol: str = "TSLA"
    timeframe: str = "1d"
    start_date: str | None = None
    end_date: str | None = None
    alpha_vantage_api_key: str | None = None
    output_dir: str = "simulation_output/rl_training"
    generated_steps: int | None = None

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

    @field_validator("algorithm", mode="before")
    @classmethod
    def normalize_algorithm(cls, value: str) -> str:
        """Accept lower/mixed-case API input while storing canonical names."""

        return value.upper() if isinstance(value, str) else value


class RLTrainingResultSchema(BaseModel):
    """Serializable metadata returned by a completed RL training job."""

    algorithm: str
    total_timesteps: int
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    environment: str
    model_path: str | None = None
    artifact_id: str | None = None


class RLTrainingJob(BaseModel):
    """Stored status document for an RL training request."""

    id: str
    status: RLTrainingStatus
    created_at: datetime
    completed_at: datetime | None = None
    request: dict[str, Any]
    result: RLTrainingResultSchema | None = None
    error: str | None = None


class RLModelArtifact(BaseModel):
    """Metadata for a saved RL model artifact."""

    id: str
    job_id: str
    algorithm: str
    path: str
    exists: bool
    size_bytes: int | None = None
    created_at: datetime


__all__ = [
    "RLAlgorithm",
    "RLEnvironment",
    "RLModelArtifact",
    "RLTrainingJob",
    "RLTrainingRequest",
    "RLTrainingResultSchema",
    "RLTrainingStatus",
]
