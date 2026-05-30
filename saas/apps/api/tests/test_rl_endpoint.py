"""Tests for RL training HTTP endpoints."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

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


@dataclass
class StubRLTrainingResult:
    model: object
    model_path: Path | None
    algorithm: str
    total_timesteps: int
    hyperparameters: dict[str, object]


def test_rl_training_lifecycle_and_model_artifact(
    monkeypatch, tmp_path
) -> None:  # noqa: ANN001
    from app.api.v1.endpoints import rl

    def stub_run_training_job(request):  # noqa: ANN001
        model_path = tmp_path / "ppo_test_model.zip"
        model_path.write_text("stub model\n")
        return StubRLTrainingResult(
            model=object(),
            model_path=model_path,
            algorithm=request.algorithm,
            total_timesteps=request.total_timesteps,
            hyperparameters={"learning_rate": 0.001},
        )

    monkeypatch.setattr(rl, "_run_training_job", stub_run_training_job)
    token = register_and_login()

    create_response = client.post(
        "/api/v1/rl/train",
        json={
            "algorithm": "PPO",
            "total_timesteps": 128,
            "hyperparameters": {"learning_rate": 0.001},
            "model_name": "ppo_test_model",
            "output_dir": str(tmp_path),
        },
        headers=auth_headers(token),
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["status"] == "completed"
    assert body["result"]["algorithm"] == "PPO"
    assert body["result"]["total_timesteps"] == 128
    assert body["result"]["model_path"].endswith("ppo_test_model.zip")

    job_response = client.get(
        f"/api/v1/rl/jobs/{body['id']}",
        headers=auth_headers(token),
    )
    artifact_response = client.get(
        f"/api/v1/rl/models/{body['result']['artifact_id']}",
        headers=auth_headers(token),
    )

    assert job_response.status_code == 200
    assert job_response.json()["id"] == body["id"]
    assert artifact_response.status_code == 200
    artifact = artifact_response.json()
    assert artifact["exists"] is True
    assert artifact["size_bytes"] > 0


def test_rl_training_validates_pivot_grid_algorithm() -> None:
    token = register_and_login()

    response = client.post(
        "/api/v1/rl/train",
        json={"algorithm": "SAC", "total_timesteps": 128},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert "SAC requires a continuous Box action-space" in response.json()["detail"]


def test_rl_jobs_are_user_scoped(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    from app.api.v1.endpoints import rl

    def stub_run_training_job(request):  # noqa: ANN001
        return StubRLTrainingResult(
            model=object(),
            model_path=None,
            algorithm=request.algorithm,
            total_timesteps=request.total_timesteps,
            hyperparameters={},
        )

    monkeypatch.setattr(rl, "_run_training_job", stub_run_training_job)
    first_token = register_and_login()
    second_token = register_and_login()

    create_response = client.post(
        "/api/v1/rl/train",
        json={"algorithm": "DQN", "total_timesteps": 64, "output_dir": str(tmp_path)},
        headers=auth_headers(first_token),
    )
    job_id = create_response.json()["id"]

    other_user_response = client.get(
        f"/api/v1/rl/jobs/{job_id}",
        headers=auth_headers(second_token),
    )

    assert create_response.status_code == 201
    assert other_user_response.status_code == 404
