"""Business service modules."""

__all__ = [
    "SimulationParameters",
    "ParameterSpec",
    "strategy_parameter_specs",
    "SimulationResult",
    "SimulationRunner",
    "run_simulation",
    "RLTrainer",
    "RLTrainingConfig",
    "RLTrainingResult",
    "NotificationAttachment",
    "NotificationDeliveryResult",
    "NotificationError",
    "NotificationService",
]


def __getattr__(name: str):
    """Lazily expose service classes without importing ML deps eagerly."""

    if name in {
        "SimulationParameters",
        "ParameterSpec",
        "strategy_parameter_specs",
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
        from app.services.strategy_settings import ParameterSpec, strategy_parameter_specs

        exports = {
            "SimulationParameters": SimulationParameters,
            "ParameterSpec": ParameterSpec,
            "strategy_parameter_specs": strategy_parameter_specs,
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

    if name in {
        "NotificationAttachment",
        "NotificationDeliveryResult",
        "NotificationError",
        "NotificationService",
    }:
        from app.services.notifications import (
            NotificationAttachment,
            NotificationDeliveryResult,
            NotificationError,
            NotificationService,
        )

        exports = {
            "NotificationAttachment": NotificationAttachment,
            "NotificationDeliveryResult": NotificationDeliveryResult,
            "NotificationError": NotificationError,
            "NotificationService": NotificationService,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
