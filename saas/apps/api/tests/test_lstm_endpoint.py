"""Tests for standalone LSTM generation endpoints."""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_and_login() -> str:
    suffix = uuid4().hex
    payload = {
        "email": f"{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": "correct-horse-battery-staple",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def candle_rows(count: int = 6) -> list[dict[str, object]]:
    return [
        {
            "timestamp": f"2024-01-{index + 1:02d}T00:00:00Z",
            "symbol": "MSFT",
            "open": 100 + index,
            "high": 101 + index,
            "low": 99 + index,
            "close": 100.5 + index,
            "volume": 1_000 + index,
        }
        for index in range(count)
    ]


class StubLSTMGenerator:
    def generate(self, seed_data, num_steps: int, features_list: list[str]):  # noqa: ANN001
        assert seed_data.shape == (2, 5)
        return pd.DataFrame(
            [
                {
                    "Open": 200.0 + index,
                    "High": 201.0 + index,
                    "Low": 199.0 + index,
                    "Close": 200.5 + index,
                    "Volume": 2_000.0 + index,
                }
                for index in range(num_steps)
            ],
            columns=features_list,
        )


def test_lstm_training_generation_lifecycle(monkeypatch) -> None:  # noqa: ANN001
    from app.api.v1.endpoints import lstm

    def stub_run_training_job(request):  # noqa: ANN001
        return (
            StubLSTMGenerator(),
            {"success": True, "message": "Model trained successfully", "final_loss": 0.123},
            np.zeros((request.sequence_length, len(request.features))),
        )

    monkeypatch.setattr(lstm, "_run_training_job", stub_run_training_job)
    token = register_and_login()

    train_response = client.post(
        "/api/v1/lstm/train",
        json={
            "rows": candle_rows(),
            "features": ["Open", "High", "Low", "Close", "Volume"],
            "sequence_length": 2,
            "lstm_units_1": 4,
            "lstm_units_2": 4,
            "epochs": 1,
            "batch_size": 2,
        },
        headers=auth_headers(token),
    )

    assert train_response.status_code == 201
    job = train_response.json()
    assert job["status"] == "completed"
    assert job["result"]["features"] == ["Open", "High", "Low", "Close", "Volume"]
    assert job["result"]["sequence_length"] == 2
    assert job["result"]["final_loss"] == 0.123

    job_response = client.get(
        f"/api/v1/lstm/jobs/{job['id']}",
        headers=auth_headers(token),
    )
    generate_response = client.post(
        "/api/v1/lstm/generate",
        json={"job_id": job["id"], "num_steps": 3},
        headers=auth_headers(token),
    )

    assert job_response.status_code == 200
    assert job_response.json()["id"] == job["id"]
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert generated["row_count"] == 3
    assert generated["rows"][0]["close"] == 200.5
    assert generated["rows"][0]["features"]["Volume"] == 2000.0


def test_lstm_jobs_are_user_scoped(monkeypatch) -> None:  # noqa: ANN001
    from app.api.v1.endpoints import lstm

    def stub_run_training_job(request):  # noqa: ANN001
        return (
            StubLSTMGenerator(),
            {"success": True, "message": "Model trained successfully"},
            np.zeros((request.sequence_length, len(request.features))),
        )

    monkeypatch.setattr(lstm, "_run_training_job", stub_run_training_job)
    first_token = register_and_login()
    second_token = register_and_login()

    create_response = client.post(
        "/api/v1/lstm/train",
        json={"rows": candle_rows(), "sequence_length": 2},
        headers=auth_headers(first_token),
    )
    job_id = create_response.json()["id"]

    other_user_response = client.get(
        f"/api/v1/lstm/jobs/{job_id}",
        headers=auth_headers(second_token),
    )

    assert create_response.status_code == 201
    assert other_user_response.status_code == 404


def test_lstm_train_validates_sequence_window() -> None:
    token = register_and_login()

    response = client.post(
        "/api/v1/lstm/train",
        json={"rows": candle_rows(3), "sequence_length": 2},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
