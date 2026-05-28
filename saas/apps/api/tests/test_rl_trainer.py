"""Tests for the standalone RL trainer configuration layer."""

import sys
import types

import pytest

from app.services.rl_trainer import RLTrainer, RLTrainingConfig


def test_training_config_accepts_readme_and_runner_aliases() -> None:
    config = RLTrainingConfig.from_mapping(
        {
            "rl_algorithm": "a2c",
            "ppo_total_timesteps": 321,
            "algo_hyperparams": {"A2C": {"learning_rate": 0.001}},
            "rl_policy": "MlpPolicy",
            "rl_model_name": "custom_model",
            "ignored": "value",
        }
    )

    assert config.normalized_algorithm() == "A2C"
    assert config.total_timesteps == 321
    assert config.hyperparameters == {"A2C": {"learning_rate": 0.001}}
    assert config.model_name == "custom_model"


def test_resolve_hyperparameters_merges_nested_algorithm_overrides() -> None:
    hyperparameters = RLTrainer.resolve_hyperparameters(
        "PPO",
        {
            "PPO": {"learning_rate": 0.001, "n_steps": 128},
            "DQN": {"learning_rate": 0.002},
        },
    )

    assert hyperparameters["learning_rate"] == 0.001
    assert hyperparameters["n_steps"] == 128
    assert hyperparameters["gamma"] == 0.99
    assert "DQN" not in hyperparameters


def test_sac_reports_project_action_space_limitation(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeBox:
        pass

    class FakeDiscrete:
        def __init__(self, size: int) -> None:
            self.size = size

    fake_spaces = types.SimpleNamespace(Box=FakeBox, Discrete=FakeDiscrete)
    monkeypatch.setitem(sys.modules, "gymnasium", types.SimpleNamespace(spaces=fake_spaces))
    monkeypatch.setitem(sys.modules, "gymnasium.spaces", fake_spaces)
    trainer = RLTrainer(env_factory=lambda: None, output_dir="unused")

    with pytest.raises(ValueError, match="PivotEnv currently uses Discrete"):
        trainer._validate_action_space("SAC", FakeDiscrete(5))


def test_resolve_hyperparameters_ignores_other_algorithm_nested_overrides() -> None:
    hyperparameters = RLTrainer.resolve_hyperparameters(
        "A2C", {"PPO": {"learning_rate": 0.001}}
    )

    assert hyperparameters["learning_rate"] == 0.0007
    assert "PPO" not in hyperparameters
