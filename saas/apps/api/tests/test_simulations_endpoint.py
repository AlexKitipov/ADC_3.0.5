"""Tests for simulation runner HTTP endpoints."""

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
class StubSimulationResult:
    output_dir: str
    historical_data_path: str
    generated_data_path: str
    orders_path: str
    trades_path: str
    performance_path: str
    rewards_path: str
    equity_curve_path: str
    drawdown_path: str
    model_path: str | None
    equity_chart_path: str | None
    drawdown_chart_path: str | None
    performance: dict[str, object]
    total_steps: int
    trained_lstm: bool
    trained_rl: bool

    def to_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


class StubSimulationRunner:
    def run(self, params):  # noqa: ANN001 - mirrors production runner signature.
        output_dir = Path(params.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "historical_data_path": output_dir / "historical_df.csv",
            "generated_data_path": output_dir / "generated_df.csv",
            "orders_path": output_dir / "orders.csv",
            "trades_path": output_dir / "trades.csv",
            "performance_path": output_dir / "performance.json",
            "rewards_path": output_dir / "rewards.csv",
            "equity_curve_path": output_dir / "equity_curve.csv",
            "drawdown_path": output_dir / "drawdown.csv",
        }
        for path in artifacts.values():
            path.write_text("stub\n")
        return StubSimulationResult(
            output_dir=str(output_dir),
            **{key: str(value) for key, value in artifacts.items()},
            model_path=None,
            equity_chart_path=None,
            drawdown_chart_path=None,
            performance={"symbol": params.symbol, "total_return": 0.12},
            total_steps=7,
            trained_lstm=params.train_lstm,
            trained_rl=params.train_rl,
        )


def test_simulation_run_lifecycle_and_artifacts(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    from app.api.v1.endpoints import simulations

    monkeypatch.setattr(simulations, "SimulationRunner", StubSimulationRunner)
    token = register_and_login()

    create_response = client.post(
        "/api/v1/simulations",
        json={
            "symbol": "MSFT",
            "output_dir": str(tmp_path / "sim"),
            "train_lstm": False,
            "train_rl": False,
            "generated_steps": 5,
        },
        headers=auth_headers(token),
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["status"] == "completed"
    assert body["parameters"]["symbol"] == "MSFT"
    assert body["result"]["total_steps"] == 7
    assert body["result"]["performance"] == {"symbol": "MSFT", "total_return": 0.12}

    simulation_id = body["id"]
    get_response = client.get(
        f"/api/v1/simulations/{simulation_id}", headers=auth_headers(token)
    )
    artifacts_response = client.get(
        f"/api/v1/simulations/{simulation_id}/artifacts",
        headers=auth_headers(token),
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == simulation_id
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert {artifact["name"] for artifact in artifacts} >= {
        "historical_data",
        "generated_data",
        "performance",
    }
    assert all(artifact["exists"] for artifact in artifacts)


def test_simulation_endpoint_validates_strategy_parameters() -> None:
    token = register_and_login()

    response = client.post(
        "/api/v1/simulations",
        json={"symbol": "", "timeframe": "2h"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert "symbol must not be empty" in response.json()["detail"]


def test_simulation_runs_are_user_scoped(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    from app.api.v1.endpoints import simulations

    monkeypatch.setattr(simulations, "SimulationRunner", StubSimulationRunner)
    first_token = register_and_login()
    second_token = register_and_login()

    create_response = client.post(
        "/api/v1/simulations",
        json={"output_dir": str(tmp_path / "private")},
        headers=auth_headers(first_token),
    )
    simulation_id = create_response.json()["id"]

    other_user_response = client.get(
        f"/api/v1/simulations/{simulation_id}", headers=auth_headers(second_token)
    )

    assert create_response.status_code == 201
    assert other_user_response.status_code == 404
