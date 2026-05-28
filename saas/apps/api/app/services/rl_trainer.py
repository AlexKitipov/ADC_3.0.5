"""Stable-Baselines RL training helpers for ADC pivot-grid environments.

This module keeps the larger RL concerns separate from the simulation runner:
algorithm selection, default/tuned hyperparameters, action-space validation,
training, and model persistence.  Heavy Stable-Baselines imports are delayed
until training time so smoke tests can run without initializing ML backends.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol


class SupportsSpaces(Protocol):
    """Small protocol for Gym/Gymnasium envs used by the trainer."""

    action_space: Any
    observation_space: Any


SUPPORTED_RL_ALGORITHMS = ("PPO", "DQN", "A2C", "SAC")

DEFAULT_RL_HYPERPARAMETERS: dict[str, dict[str, Any]] = {
    "PPO": {
        "learning_rate": 3e-4,
        "n_steps": 2048,
        "batch_size": 64,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_range": 0.2,
        "ent_coef": 0.0,
    },
    "DQN": {
        "learning_rate": 1e-4,
        "buffer_size": 100_000,
        "learning_starts": 1_000,
        "batch_size": 32,
        "gamma": 0.99,
        "train_freq": 4,
        "target_update_interval": 1_000,
        "exploration_fraction": 0.1,
        "exploration_final_eps": 0.05,
    },
    "A2C": {
        "learning_rate": 7e-4,
        "n_steps": 5,
        "gamma": 0.99,
        "gae_lambda": 1.0,
        "ent_coef": 0.0,
        "vf_coef": 0.5,
    },
    "SAC": {
        "learning_rate": 3e-4,
        "buffer_size": 100_000,
        "learning_starts": 1_000,
        "batch_size": 256,
        "gamma": 0.99,
        "train_freq": 1,
        "gradient_steps": 1,
        "ent_coef": "auto",
    },
}


@dataclass(slots=True)
class RLTrainingConfig:
    """Configuration for a single Stable-Baselines training run."""

    algorithm: str = "PPO"
    total_timesteps: int = 50_000
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    policy: str = "MlpPolicy"
    model_name: str | None = None
    save_model: bool = True
    seed: int | None = None
    verbose: int = 0
    device: str = "auto"

    @classmethod
    def from_mapping(cls, params: Mapping[str, Any] | None = None) -> "RLTrainingConfig":
        """Create a config from API/UI parameters while accepting README aliases."""

        if params is None:
            return cls()

        aliases = {
            "rl_algorithm": "algorithm",
            "ppo_total_timesteps": "total_timesteps",
            "rl_total_timesteps": "total_timesteps",
            "algo_hyperparams": "hyperparameters",
            "rl_hyperparameters": "hyperparameters",
            "rl_policy": "policy",
            "rl_model_name": "model_name",
        }
        fields = cls.__dataclass_fields__
        normalized: dict[str, Any] = {}
        for key, value in params.items():
            target = aliases.get(key, key)
            if target in fields:
                normalized[target] = value
        return cls(**normalized)

    def normalized_algorithm(self) -> str:
        return self.algorithm.upper()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["algorithm"] = self.normalized_algorithm()
        return payload


@dataclass(slots=True)
class RLTrainingResult:
    """Result returned after an RL model has been trained and optionally saved."""

    model: Any
    model_path: Path | None
    algorithm: str
    total_timesteps: int
    hyperparameters: dict[str, Any]


class RLTrainer:
    """Train and persist Stable-Baselines models for ADC environments."""

    def __init__(
        self, env_factory: Callable[[], SupportsSpaces], output_dir: str | Path
    ) -> None:
        self.env_factory = env_factory
        self.output_dir = Path(output_dir)

    def train(self, config: RLTrainingConfig | Mapping[str, Any] | None = None) -> RLTrainingResult:
        """Train a PPO/DQN/A2C/SAC model and save it when configured."""

        training_config = (
            config if isinstance(config, RLTrainingConfig) else RLTrainingConfig.from_mapping(config)
        )
        algorithm = training_config.normalized_algorithm()
        if algorithm not in SUPPORTED_RL_ALGORITHMS:
            supported = ", ".join(SUPPORTED_RL_ALGORITHMS)
            raise ValueError(
                f"Unsupported RL algorithm: {training_config.algorithm}. Supported: {supported}."
            )

        vec_env = self._make_vec_env()
        self._validate_action_space(algorithm, vec_env.action_space)

        model_classes = self._load_model_classes()
        hyperparameters = self.resolve_hyperparameters(algorithm, training_config.hyperparameters)
        model = model_classes[algorithm](
            training_config.policy,
            vec_env,
            verbose=training_config.verbose,
            seed=training_config.seed,
            device=training_config.device,
            **hyperparameters,
        )
        model.learn(total_timesteps=training_config.total_timesteps)

        model_path = None
        if training_config.save_model:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            model_path = self._save_model(model, algorithm, training_config.model_name)

        return RLTrainingResult(
            model=model,
            model_path=model_path,
            algorithm=algorithm,
            total_timesteps=training_config.total_timesteps,
            hyperparameters=hyperparameters,
        )

    @staticmethod
    def resolve_hyperparameters(algorithm: str, overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Merge project defaults with either flat or per-algorithm overrides."""

        normalized_algorithm = algorithm.upper()
        if normalized_algorithm not in DEFAULT_RL_HYPERPARAMETERS:
            supported = ", ".join(SUPPORTED_RL_ALGORITHMS)
            raise ValueError(f"Unsupported RL algorithm: {algorithm}. Supported: {supported}.")

        resolved = dict(DEFAULT_RL_HYPERPARAMETERS[normalized_algorithm])
        if not overrides:
            return resolved

        algorithm_overrides = {str(key).upper(): value for key, value in overrides.items()}
        if normalized_algorithm in algorithm_overrides and isinstance(
            algorithm_overrides[normalized_algorithm], Mapping
        ):
            resolved.update(algorithm_overrides[normalized_algorithm])
        elif set(algorithm_overrides).issubset(set(SUPPORTED_RL_ALGORITHMS)):
            return resolved
        else:
            resolved.update(overrides)
        return resolved

    def _make_vec_env(self) -> Any:
        vec_env_module = import_module("stable_baselines3.common.vec_env")
        return vec_env_module.DummyVecEnv([self.env_factory])

    def _load_model_classes(self) -> dict[str, Any]:
        stable_baselines = import_module("stable_baselines3")
        return {
            "PPO": stable_baselines.PPO,
            "DQN": stable_baselines.DQN,
            "A2C": stable_baselines.A2C,
            "SAC": stable_baselines.SAC,
        }

    def _validate_action_space(self, algorithm: str, action_space: Any) -> None:
        spaces = import_module("gymnasium.spaces")
        if algorithm == "DQN" and not isinstance(action_space, spaces.Discrete):
            raise ValueError("DQN requires a discrete action space.")
        if algorithm == "SAC" and not isinstance(action_space, spaces.Box):
            raise ValueError(
                "SAC is registered, but it requires a continuous Box action space. "
                "PivotEnv currently uses Discrete(5), so choose PPO, DQN, or A2C for this project "
                "or add a continuous-action environment before training SAC."
            )

    def _save_model(self, model: Any, algorithm: str, model_name: str | None = None) -> Path:
        base_name = model_name or f"{algorithm.lower()}_pivot_model_v2"
        target = self.output_dir / base_name
        model.save(str(target))
        return target.with_suffix(".zip")
