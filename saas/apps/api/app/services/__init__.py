"""Business service modules."""

__all__ = [
    "SimulationParameters",
    "SimulationResult",
    "SimulationRunner",
    "run_simulation",
]


def __getattr__(name: str):
    """Lazily expose the simulation runner without importing ML deps eagerly."""

    if name in __all__:
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
