"""Business service modules."""

__all__ = [
    "SimulationParameters",
    "SimulationResult",
    "SimulationRunner",
    "run_simulation",
    "RLTrainer",
    "RLTrainingConfig",
    "RLTrainingResult",
]


def __getattr__(name: str):
    """Lazily expose service classes without importing ML deps eagerly."""

    if name in {
        "SimulationParameters",
        "SimulationResult",
        "SimulationRunner",
        "run_simulation",
    }:
        from app.services.simulation_runner import (
            SimulationParameters,
            SimulationResult,
            SimulationRunner,
            run_simulation,
        )

        exports = {
            "SimulationParameters": SimulationParameters,
            "SimulationResult": SimulationResult,
            "SimulationRunner": SimulationRunner,
            "run_simulation": run_simulation,
        }
        return exports[name]

    if name in {"RLTrainer", "RLTrainingConfig", "RLTrainingResult"}:
        from app.services.rl_trainer import RLTrainer, RLTrainingConfig, RLTrainingResult

        exports = {
            "RLTrainer": RLTrainer,
            "RLTrainingConfig": RLTrainingConfig,
            "RLTrainingResult": RLTrainingResult,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
