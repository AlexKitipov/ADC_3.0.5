"""Startup smoke checks for the MVP FastAPI runtime."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]


def _run_startup_smoke(code: str) -> subprocess.CompletedProcess[str]:
    if importlib.util.find_spec("fastapi") is None:
        pytest.skip("FastAPI is not installed in this execution environment")
    return subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        cwd=API_ROOT,
        capture_output=True,
        text=True,
    )


def test_health_endpoint_returns_ok() -> None:
    """The versioned health endpoint is available on the single FastAPI app."""

    result = _run_startup_smoke(
        """
from fastapi.testclient import TestClient
from app.main import app

response = TestClient(app).get("/api/v1/health")
assert response.status_code == 200
assert response.json() == {"status": "ok"}
print(response.json()["status"])
"""
    )

    assert result.stdout.strip() == "ok"


def test_app_import_does_not_load_optional_lab_or_worker_runtimes() -> None:
    """Importing app.main should not import worker, RL environment, or LSTM code."""

    result = _run_startup_smoke(
        """
import sys
from app.main import app

blocked_modules = [
    "app.workers",
    "app.workers.celery",
    "app.services.simulation_runner",
    "app.services.pivot_env",
    "core.lstm_model",
]
loaded = [name for name in blocked_modules if name in sys.modules]
if loaded:
    raise SystemExit(f"optional runtime modules imported at startup: {loaded}")
print(app.title)
"""
    )

    assert result.stdout.strip() == "ADC Trading Platform"
