"""Simulation runner API endpoints."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.schemas import SimulationArtifact, SimulationRequest, SimulationRun
from app.security import get_current_user
from app.services.simulation_runner import SimulationRunner
from app.services.strategy_settings import SimulationParameters

router = APIRouter()

# In-process storage keeps the first HTTP workflow lightweight and deterministic
# for smoke tests.  The response shape is intentionally compatible with moving
# execution to Celery later: POST creates a run document, GET reads by id.
_SIMULATION_RUNS: dict[str, dict[str, object]] = {}


@router.post("", response_model=SimulationRun, status_code=status.HTTP_201_CREATED)
def create_simulation(
    request: SimulationRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Run a simulation synchronously and store its status/result by id."""

    parameters = _build_parameters(request)
    run_id = uuid4().hex
    run_record: dict[str, object] = {
        "id": run_id,
        "user_id": current_user.id,
        "status": "running",
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "parameters": parameters.to_dict(),
        "result": None,
        "error": None,
    }
    _SIMULATION_RUNS[run_id] = run_record

    try:
        result = SimulationRunner().run(parameters)
    except Exception as exc:  # pragma: no cover - failures are data/env dependent.
        run_record.update(
            {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error": str(exc),
            }
        )
    else:
        run_record.update(
            {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "result": result.to_dict(),
            }
        )

    return _public_run(run_record)


@router.get("/{simulation_id}", response_model=SimulationRun)
def get_simulation(
    simulation_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Return a stored simulation status/result document."""

    return _public_run(_get_user_run(simulation_id, current_user))


@router.get("/{simulation_id}/artifacts", response_model=list[SimulationArtifact])
def list_simulation_artifacts(
    simulation_id: str,
    current_user: User = Depends(get_current_user),
) -> list[SimulationArtifact]:
    """Return the artifact files emitted by a completed simulation."""

    run_record = _get_user_run(simulation_id, current_user)
    if run_record["status"] != "completed" or run_record.get("result") is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation artifacts are only available for completed runs.",
        )

    result = run_record["result"]
    assert isinstance(result, dict)
    artifact_fields = {
        "historical_data": "historical_data_path",
        "generated_data": "generated_data_path",
        "orders": "orders_path",
        "trades": "trades_path",
        "performance": "performance_path",
        "rewards": "rewards_path",
        "equity_curve": "equity_curve_path",
        "drawdown": "drawdown_path",
        "model": "model_path",
        "equity_chart": "equity_chart_path",
        "drawdown_chart": "drawdown_chart_path",
    }
    artifacts: list[SimulationArtifact] = []
    for name, field_name in artifact_fields.items():
        artifact_path = result.get(field_name)
        if not artifact_path:
            continue
        path = Path(str(artifact_path))
        artifacts.append(
            SimulationArtifact(
                name=name,
                path=str(path),
                exists=path.exists(),
                size_bytes=path.stat().st_size if path.exists() else None,
            )
        )
    return artifacts


def _build_parameters(request: SimulationRequest) -> SimulationParameters:
    try:
        return SimulationParameters.from_mapping(request.model_dump(exclude_none=True))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _get_user_run(simulation_id: str, current_user: User) -> dict[str, object]:
    run_record = _SIMULATION_RUNS.get(simulation_id)
    if run_record is None or run_record.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    return run_record


def _public_run(run_record: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in run_record.items() if key != "user_id"}
