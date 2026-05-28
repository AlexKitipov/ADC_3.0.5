"""Tests for typed backend strategy settings."""

from pathlib import Path

import pandas as pd
import pytest

from app.services.pivot_env import PivotEnv
from app.services.strategy_settings import SimulationParameters, strategy_parameter_specs


def test_strategy_settings_accept_widget_aliases_and_coerce_values(tmp_path: Path) -> None:
    params = SimulationParameters.from_mapping(
        {
            "ppo_total_timesteps": "123",
            "base_path": str(tmp_path),
            "balance": "2500.5",
            "train_lstm": "false",
            "adaptive_averaging_enabled": "true",
            "ignored_widget_key": "ignored",
        }
    )

    assert params.rl_total_timesteps == 123
    assert params.output_dir == str(tmp_path)
    assert params.initial_balance == 2500.5
    assert params.train_lstm is False
    assert params.adaptive_averaging_enabled is True


def test_strategy_settings_validate_ranges_options_and_date_order() -> None:
    with pytest.raises(ValueError, match="grid_levels"):
        SimulationParameters(grid_levels=0)

    with pytest.raises(ValueError, match="timeframe"):
        SimulationParameters(timeframe="2h")

    with pytest.raises(ValueError, match="start_date"):
        SimulationParameters(start_date="2024-02-01", end_date="2024-01-01")


def test_strategy_settings_prepare_env_and_rl_config() -> None:
    params = SimulationParameters.from_mapping(
        {
            "rl_algorithm": "DQN",
            "ppo_total_timesteps": 1000,
            "algo_hyperparams": {"DQN": {"learning_rate": 0.001}},
            "balance": 3000,
            "grid_levels": 2,
        }
    )

    env_kwargs = params.env_kwargs()
    training_config = params.to_rl_training_config()

    assert env_kwargs["initial_balance"] == 3000.0
    assert env_kwargs["grid_levels"] == 2
    assert training_config.algorithm == "DQN"
    assert training_config.total_timesteps == 1000
    assert training_config.hyperparameters == {"DQN": {"learning_rate": 0.001}}


def test_strategy_parameter_specs_expose_widget_metadata() -> None:
    specs = {spec["name"]: spec for spec in strategy_parameter_specs()}

    assert specs["timeframe"]["options"] == ["1d", "5min", "15min", "30min", "60min"]
    assert specs["grid_levels"]["default"] == 3
    assert specs["rl_algorithm"]["options"] == ["PPO", "DQN", "A2C", "SAC"]


def test_pivot_env_resets_to_configured_initial_balance() -> None:
    frame = pd.DataFrame(
        {
            "Open": [1.0, 1.1],
            "High": [1.2, 1.3],
            "Low": [0.9, 1.0],
            "Close": [1.1, 1.2],
            "Volume": [100, 100],
            "RSI": [50, 55],
            "MACD": [0.1, 0.2],
            "MACD_Signal": [0.05, 0.1],
            "RSI_Cross_Count": [0, 1],
            "Bb_Middle": [1.0, 1.1],
            "Bb_Upper": [1.2, 1.3],
            "Bb_Lower": [0.8, 0.9],
            "ATR": [0.1, 0.1],
            "Pivot": [1.0, 1.1],
            "R1": [1.2, 1.3],
            "S1": [0.8, 0.9],
            "R2": [1.4, 1.5],
            "S2": [0.6, 0.7],
        }
    )
    env = PivotEnv(frame, frame, broker_api=None, order_manager=None, initial_balance=4321.0)
    env.balance = 1.0
    env.open_trades = [{"entry_price": 1.0}]
    env.pending_orders = [{"entry_price": 1.0}]

    _, info = env.reset()

    assert info == {}
    assert env.balance == 4321.0
    assert env.max_equity_so_far == 4321.0
    assert env.open_trades == []
    assert env.pending_orders == []
