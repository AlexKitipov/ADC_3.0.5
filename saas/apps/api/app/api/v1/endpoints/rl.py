"""Reinforcement-learning training endpoints."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.schemas import RLModelArtifact, RLTrainingJob, RLTrainingRequest
from app.security import get_current_user
from app.services.data_loader import DataLoader
from app.services.rl_trainer import RLTrainingConfig
from app.services.simulation_runner import SimulationRunner
from app.services.strategy_settings import SimulationParameters

router = APIRouter()

# RL jobs intentionally use the same status-document pattern as simulations.
# This PR executes jobs synchronously so tests and local runs are deterministic;
# the stored document shape can be backed by Celery task ids in a future worker
# implementation without changing clients.
_RL_JOBS: dict[str, dict[str, object]] = {}
_RL_MODELS: dict[str, dict[str, object]] = {}
PIVOT_GRID_ALGORITHMS = {"PPO", "DQN", "A2C"}


@router.post("/train", response_model=RLTrainingJob, status_code=status.HTTP_201_CREATED)
def create_rl_training_job(
    request: RLTrainingRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Train an RL model for the pivot-grid environment and store job status."""

    _validate_environment_algorithm(request)
    job_id = uuid4().hex
    request_payload = request.model_dump()
    job_record: dict[str, object] = {
        "id": job_id,
        "user_id": current_user.id,
        "status": "running",
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "request": request_payload,
        "result": None,
        "error": None,
    }
    _RL_JOBS[job_id] = job_record

    try:
        result = _run_training_job(request)
    except HTTPException:
        _RL_JOBS.pop(job_id, None)
        raise
    except Exception as exc:  # pragma: no cover - depends on data/ML runtime.
        job_record.update(
            {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error": str(exc),
            }
        )
    else:
        artifact_id = None
        model_path = result.model_path
        if model_path is not None:
            artifact_id = uuid4().hex
            _RL_MODELS[artifact_id] = {
                "id": artifact_id,
                "job_id": job_id,
                "user_id": current_user.id,
                "algorithm": result.algorithm,
                "path": str(model_path),
                "exists": model_path.exists(),
                "size_bytes": model_path.stat().st_size if model_path.exists() else None,
                "created_at": datetime.utcnow(),
            }

        job_record.update(
            {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "result": {
                    "algorithm": result.algorithm,
                    "total_timesteps": result.total_timesteps,
                    "hyperparameters": result.hyperparameters,
                    "environment": request.environment,
                    "model_path": str(model_path) if model_path else None,
                    "artifact_id": artifact_id,
                },
            }
        )

    return _public_job(job_record)


@router.get("/jobs/{job_id}", response_model=RLTrainingJob)
def get_rl_training_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Return a stored RL training status/result document."""

    return _public_job(_get_user_job(job_id, current_user))


@router.get("/models/{model_id}", response_model=RLModelArtifact)
def get_rl_model_artifact(
    model_id: str,
    current_user: User = Depends(get_current_user),
) -> RLModelArtifact:
    """Return metadata for a saved RL model artifact."""

    artifact = _RL_MODELS.get(model_id)
    if artifact is None or artifact.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="RL model not found"
        )

    public_artifact = {key: value for key, value in artifact.items() if key != "user_id"}
    path = Path(str(public_artifact["path"]))
    public_artifact["exists"] = path.exists()
    public_artifact["size_bytes"] = path.stat().st_size if path.exists() else None
    return RLModelArtifact(**public_artifact)


def _run_training_job(request: RLTrainingRequest):  # noqa: ANN201 - returns RLTrainingResult.
    params = _build_simulation_parameters(request)
    if params.random_seed is not None:
        import numpy as np

        np.random.seed(params.random_seed)

    output_dir = params.ensure_output_dir()
    runner = SimulationRunner()
    loader = DataLoader(params.alpha_vantage_api_key)
    raw_data = loader.fetch_data(
        params.symbol,
        timeframe=params.timeframe,
        start_date=params.start_date,
        end_date=params.end_date,
    )
    historical_df = runner._prepare_historical_data(raw_data)
    generated_df, _ = runner._generate_lstm_data(historical_df, params)
    historical_df, generated_df = runner._align_frames(historical_df, generated_df)

    training_config = RLTrainingConfig(
        algorithm=request.algorithm,
        total_timesteps=request.total_timesteps,
        hyperparameters=request.hyperparameters,
        policy=request.policy,
        model_name=request.model_name,
        save_model=request.save_model,
        seed=request.seed,
        verbose=request.verbose,
        device=request.device,
    )
    from app.services.rl_trainer import RLTrainer

    rl_trainer = RLTrainer(
        env_factory=lambda: runner._make_env(historical_df, generated_df, params),
        output_dir=output_dir,
    )
    return rl_trainer.train(training_config)


def _build_simulation_parameters(request: RLTrainingRequest) -> SimulationParameters:
    payload = request.model_dump()
    payload.update(
        {
            "rl_algorithm": request.algorithm,
            "rl_total_timesteps": request.total_timesteps,
            "algo_hyperparams": request.hyperparameters,
            "rl_policy": request.policy,
            "rl_model_name": request.model_name,
            "rl_verbose": request.verbose,
            "rl_device": request.device,
            "train_lstm": False,
            "train_rl": True,
            "save_charts": False,
            "random_seed": request.seed,
        }
    )
    try:
        return SimulationParameters.from_mapping(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _validate_environment_algorithm(request: RLTrainingRequest) -> None:
    algorithm = request.algorithm.upper()
    if request.environment == "pivot-grid" and algorithm not in PIVOT_GRID_ALGORITHMS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "pivot-grid uses a discrete action space and supports PPO, DQN, and A2C. "
                "SAC requires a continuous Box action-space environment."
            ),
        )


def _get_user_job(job_id: str, current_user: User) -> dict[str, object]:
    job_record = _RL_JOBS.get(job_id)
    if job_record is None or job_record.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="RL job not found"
        )
    return job_record


def _public_job(job_record: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in job_record.items() if key != "user_id"}
