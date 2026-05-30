"""LSTM synthetic price generation API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.market_data import OHLCVRow

LSTMJobStatus = Literal["running", "completed", "failed"]
DEFAULT_LSTM_FEATURES = ["Open", "High", "Low", "Close", "Volume"]


class LSTMTrainRequest(BaseModel):
    """Payload used to train a standalone LSTM price generator."""

    model_config = ConfigDict(extra="ignore")

    rows: list[OHLCVRow] = Field(..., min_length=3)
    features: list[str] = Field(default_factory=lambda: DEFAULT_LSTM_FEATURES.copy(), min_length=1)
    sequence_length: int = Field(default=2, ge=1, le=240)
    lstm_units_1: int = Field(default=16, ge=1, le=512)
    lstm_units_2: int = Field(default=16, ge=1, le=512)
    learning_rate: float = Field(default=0.001, gt=0, le=1)
    epochs: int = Field(default=1, ge=1, le=500)
    batch_size: int = Field(default=8, ge=1, le=2048)
    validation_split: float = Field(default=0.0, ge=0.0, lt=1.0)

    @field_validator("features")
    @classmethod
    def normalize_features(cls, value: list[str]) -> list[str]:
        """Trim feature names while preserving caller-selected casing."""

        normalized = [feature.strip() for feature in value if feature.strip()]
        if not normalized:
            raise ValueError("features must contain at least one column name")
        return normalized

    @model_validator(mode="after")
    def validate_sequence_window(self) -> "LSTMTrainRequest":
        """Require enough rows for the generator sequence preparation logic."""

        if len(self.rows) <= self.sequence_length + 1:
            raise ValueError("rows must contain more than sequence_length + 1 candles")
        return self


class LSTMGenerateRequest(BaseModel):
    """Payload used to generate candles from a completed LSTM training job."""

    job_id: str = Field(..., min_length=1)
    num_steps: int = Field(default=25, ge=1, le=1000)
    seed_rows: list[OHLCVRow] | None = None


class GeneratedCandleRow(BaseModel):
    """One generated synthetic candle row."""

    step: int
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    features: dict[str, float] = Field(default_factory=dict)


class LSTMTrainingResultSchema(BaseModel):
    """Serializable metadata returned by a completed LSTM training job."""

    features: list[str]
    sequence_length: int
    lstm_units_1: int
    lstm_units_2: int
    learning_rate: float
    epochs: int
    batch_size: int
    row_count: int
    final_loss: float | None = None
    final_val_loss: float | None = None
    message: str


class LSTMGenerationResultSchema(BaseModel):
    """Generated synthetic candle rows for a trained LSTM job."""

    job_id: str
    features: list[str]
    rows: list[GeneratedCandleRow]
    row_count: int


class LSTMJob(BaseModel):
    """Stored status document for an LSTM training request."""

    id: str
    status: LSTMJobStatus
    created_at: datetime
    completed_at: datetime | None = None
    request: dict[str, Any]
    result: LSTMTrainingResultSchema | None = None
    error: str | None = None


__all__ = [
    "DEFAULT_LSTM_FEATURES",
    "GeneratedCandleRow",
    "LSTMGenerateRequest",
    "LSTMGenerationResultSchema",
    "LSTMJob",
    "LSTMJobStatus",
    "LSTMTrainRequest",
    "LSTMTrainingResultSchema",
]
