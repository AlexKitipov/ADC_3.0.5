"""Standalone LSTM synthetic price generation endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.schemas import (
    GeneratedCandleRow,
    LSTMGenerateRequest,
    LSTMGenerationResultSchema,
    LSTMJob,
    LSTMTrainRequest,
)
from app.security import get_current_user
from core.lstm_model import LSTMPriceGenerator

router = APIRouter()

# Jobs are synchronous for deterministic smoke tests and local development.  The
# document shape mirrors RL jobs so Celery task ids can replace in-memory records
# later without changing frontend contracts.
_LSTM_JOBS: dict[str, dict[str, object]] = {}
_LSTM_MODELS: dict[str, dict[str, object]] = {}


@router.post("/train", response_model=LSTMJob, status_code=status.HTTP_201_CREATED)
def create_lstm_training_job(
    request: LSTMTrainRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Train a standalone LSTM price generator and store its status by id."""

    job_id = uuid4().hex
    request_payload = request.model_dump(mode="json")
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
    _LSTM_JOBS[job_id] = job_record

    try:
        generator, train_result, seed_sequence = _run_training_job(request)
    except HTTPException:
        _LSTM_JOBS.pop(job_id, None)
        raise
    except Exception as exc:  # pragma: no cover - depends on optional ML runtime.
        job_record.update(
            {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error": str(exc),
            }
        )
    else:
        if not train_result.get("success"):
            job_record.update(
                {
                    "status": "failed",
                    "completed_at": datetime.utcnow(),
                    "error": str(train_result.get("message", "LSTM training failed")),
                }
            )
        else:
            _LSTM_MODELS[job_id] = {
                "user_id": current_user.id,
                "generator": generator,
                "features": request.features,
                "sequence_length": request.sequence_length,
                "seed_sequence": seed_sequence,
            }
            job_record.update(
                {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "result": {
                        "features": request.features,
                        "sequence_length": request.sequence_length,
                        "lstm_units_1": request.lstm_units_1,
                        "lstm_units_2": request.lstm_units_2,
                        "learning_rate": request.learning_rate,
                        "epochs": request.epochs,
                        "batch_size": request.batch_size,
                        "row_count": len(request.rows),
                        "final_loss": train_result.get("final_loss"),
                        "final_val_loss": train_result.get("final_val_loss"),
                        "message": str(train_result.get("message", "Model trained successfully")),
                    },
                }
            )

    return _public_job(job_record)


@router.post("/generate", response_model=LSTMGenerationResultSchema)
def generate_lstm_candles(
    request: LSTMGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> LSTMGenerationResultSchema:
    """Generate synthetic candles from a completed LSTM training job."""

    model_record = _get_user_model(request.job_id, current_user)
    generator = model_record["generator"]
    features = list(model_record["features"])

    if request.seed_rows:
        seed_df = _rows_to_dataframe(request.seed_rows)
        _validate_features(seed_df, features)
        X, _, _ = generator.prepare_sequences(
            seed_df,
            features,
            int(model_record["sequence_length"]),
        )
        if len(X) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="seed_rows must contain enough candles for the job sequence_length",
            )
        seed_sequence = X[-1]
    else:
        seed_sequence = model_record["seed_sequence"]

    generated_df = generator.generate(
        np.asarray(seed_sequence),
        num_steps=request.num_steps,
        features_list=features,
    )
    rows = _generated_rows(generated_df)
    return LSTMGenerationResultSchema(
        job_id=request.job_id,
        features=features,
        rows=rows,
        row_count=len(rows),
    )


@router.get("/jobs/{job_id}", response_model=LSTMJob)
def get_lstm_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Return a stored LSTM training status/result document."""

    return _public_job(_get_user_job(job_id, current_user))


def _run_training_job(
    request: LSTMTrainRequest,
) -> tuple[LSTMPriceGenerator, dict[str, object], np.ndarray]:
    data = _rows_to_dataframe(request.rows)
    _validate_features(data, request.features)

    generator = LSTMPriceGenerator()
    train_result = generator.train(
        data,
        features=request.features,
        sequence_length=request.sequence_length,
        lstm_units_1=request.lstm_units_1,
        lstm_units_2=request.lstm_units_2,
        learning_rate=request.learning_rate,
        epochs=request.epochs,
        batch_size=request.batch_size,
        validation_split=request.validation_split,
        verbose=0,
    )
    X, _, _ = generator.prepare_sequences(data, request.features, request.sequence_length)
    seed_sequence = X[-1] if len(X) else np.array([])
    return generator, train_result, seed_sequence


def _rows_to_dataframe(rows: list[object]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for row in rows:
        if hasattr(row, "model_dump"):
            payload = row.model_dump()
        else:
            payload = dict(row)  # type: ignore[arg-type]
        records.append(
            {
                "Open": payload["open"],
                "High": payload["high"],
                "Low": payload["low"],
                "Close": payload["close"],
                "Volume": payload["volume"],
            }
        )
    return pd.DataFrame.from_records(records)


def _validate_features(data: pd.DataFrame, features: list[str]) -> None:
    missing = sorted(set(features) - set(data.columns))
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing LSTM feature columns: {missing}",
        )


def _generated_rows(generated_df: pd.DataFrame) -> list[GeneratedCandleRow]:
    rows: list[GeneratedCandleRow] = []
    for index, row in generated_df.iterrows():
        feature_values = {
            str(column): float(value)
            for column, value in row.items()
            if pd.notna(value)
        }
        rows.append(
            GeneratedCandleRow(
                step=int(index) + 1,
                open=feature_values.get("Open"),
                high=feature_values.get("High"),
                low=feature_values.get("Low"),
                close=feature_values.get("Close"),
                volume=feature_values.get("Volume"),
                features=feature_values,
            )
        )
    return rows


def _get_user_job(job_id: str, current_user: User) -> dict[str, object]:
    job_record = _LSTM_JOBS.get(job_id)
    if job_record is None or job_record.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="LSTM job not found"
        )
    return job_record


def _get_user_model(job_id: str, current_user: User) -> dict[str, object]:
    _get_user_job(job_id, current_user)
    model_record = _LSTM_MODELS.get(job_id)
    if model_record is None or model_record.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="LSTM model is not available for this job",
        )
    return model_record


def _public_job(job_record: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in job_record.items() if key != "user_id"}
