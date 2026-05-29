"""Tests for strategy parameter metadata endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_strategy_parameters_returns_backend_owned_metadata() -> None:
    response = client.get("/api/v1/strategy/parameters")

    assert response.status_code == 200
    specs = {spec["name"]: spec for spec in response.json()}

    assert specs["timeframe"] == {
        "name": "timeframe",
        "group": "data",
        "label": "Timeframe",
        "default": "1d",
        "min_value": None,
        "max_value": None,
        "step": None,
        "options": ["1d", "5min", "15min", "30min", "60min"],
        "description": "",
    }
    assert specs["grid_levels"]["min_value"] == 1
    assert specs["grid_levels"]["max_value"] == 5
    assert specs["rl_algorithm"]["options"] == ["PPO", "DQN", "A2C", "SAC"]
