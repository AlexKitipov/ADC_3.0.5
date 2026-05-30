# API App

Python backend application for ADC SaaS.

Implemented responsibilities:

- FastAPI application entry point in `app/main.py`
- Canonical REST API endpoints under `/api/v1`
- Health checks at `/api/v1/health`
- SQLAlchemy engine/session setup
- Celery application setup backed by Redis
- Environment-driven configuration for database, Redis, JWT, and SMTP settings

Core MVP endpoint responsibilities:

- Authentication and current-user profile management (`/api/v1/auth/*`)
- Dashboard statistics, equity curves, and drawdown curves (`/api/v1/dashboard/*`)
- User settings and strategy parameter metadata (`/api/v1/settings/*`, `/api/v1/strategy/parameters`)
- Signal and simple trade-record persistence (`/api/v1/signals/*`, `/api/v1/trades/*`)
- Market data, indicator calculation, simulation runs, RL jobs, and LSTM jobs
- Broker/order-management simulations and trading-session orchestration
- Market tick streaming over server-sent events
- Email notifications and trade-journal import/export workflows
- Static route contract tests that keep frontend API modules synchronized with backend routes

Readiness, health, and demo-compatible routes remain available for smoke tests
and backwards compatibility. They are intentionally not removed in this PR, but
they do not change the canonical MVP runtime direction.

## API base path

The backend registers a single canonical frontend-facing REST API namespace:
`/api/v1`. Unversioned `/api/*` resource routes are intentionally not registered.
Clients, tests, deployment configuration, and reverse proxies should target the
full versioned base URL, for example `http://localhost:8000/api/v1` in local
development.


## API documentation and contract validation

The developer-facing API reference lives in `../../docs/api/README.md`. It is
the hand-authored companion to the runtime FastAPI OpenAPI schema exposed by:

- `GET /openapi.json`
- `GET /docs`
- `GET /redoc`

Contract coverage lives in `tests/test_api_contracts.py`. The test uses static
source inspection so it can validate the expected route set, `/api/v1` base path,
frontend consumed paths, and documentation coverage without requiring optional
runtime dependencies to be installed first. Update the route contract and the API
docs in the same change whenever adding, renaming, or removing endpoints.

## Local development

The canonical MVP backend entry point is the FastAPI app in this directory. From
the repository root, start it with:

```bash
cd saas/apps/api && uvicorn app.main:app --reload
```

This serves the versioned API at `http://localhost:8000/api/v1`. The Vite
frontend should target that URL with:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

Copy the SaaS environment template before running the local stack:

```bash
cd saas && cp .env.example .env
```

The notebook and root-level legacy workflow remain archive/reference material.
They should not be used as an alternate backend entry point for MVP work.

Run the API contract test from this directory:

```bash
python -m pytest tests/test_api_contracts.py
```

Run the full API test suite when dependencies are installed:

```bash
python -m pytest
```

## Simulation runner

`app/services/simulation_runner.py` contains the backend replacement for the
notebook simulation button.  It orchestrates the full experiment pipeline:

1. collect typed `SimulationParameters` (including README aliases such as
   `ppo_total_timesteps`),
2. fetch OHLCV data through `DataLoader`,
3. calculate pivots, RSI, MACD, Bollinger Bands, ATR, and RSI cross counts,
4. train/generate LSTM synthetic data when enabled, with a deterministic
   historical fallback for smoke tests or short datasets,
5. train a PPO/DQN/A2C agent on `PivotEnv` when enabled,
6. replay the policy and persist CSV/JSON/PNG artifacts under `output_dir`.

Minimal smoke run without heavy ML training:

```python
from app.services.simulation_runner import run_simulation

result = run_simulation({
    "symbol": "TSLA",
    "start_date": "2024-01-01",
    "end_date": "2024-06-01",
    "output_dir": "simulation_output",
    "train_lstm": False,
    "train_rl": False,
    "save_charts": False,
})
print(result.to_dict())
```

Production-style runs can leave `train_lstm=True` and `train_rl=True` and tune
`rl_algorithm`, `rl_total_timesteps`, `algo_hyperparams`, and the pivot-grid
parameters exposed by `SimulationParameters`.

## Strategy settings module

`app/services/strategy_settings.py` is the backend replacement for the Colab
widget parameter dictionaries. It centralizes the simulation configuration by:

- defining typed `SimulationParameters` for data loading, LSTM generation, RL
  training, pivot-grid rules, adaptive averaging, filters, output settings, and
  smoke-test flags;
- accepting README/widget aliases such as `ppo_total_timesteps`, `base_path`,
  `alpha_key`, and `balance`;
- coercing API payload values into the expected Python types and validating
  supported timeframes, RL algorithms, date ordering, and numeric ranges;
- exposing `env_kwargs()` and `to_rl_training_config()` so the simulation runner
  can prepare `PivotEnv` and `RLTrainer` without duplicating parameter lists;
- exposing `strategy_parameter_specs()` metadata for future API/UI forms.

Example:

```python
from app.services.strategy_settings import SimulationParameters

params = SimulationParameters.from_mapping({
    "symbol": "EURUSD=X",
    "ppo_total_timesteps": 10_000,
    "balance": 25_000,
    "grid_levels": 3,
    "train_lstm": False,
    "train_rl": False,
})
print(params.env_kwargs())
```

## Notification service

`app/services/notifications.py` provides the backend notification layer for
email delivery, file attachments, and completed simulation result messages. It
uses the existing SMTP environment settings (`SMTP_SERVER`, `SMTP_PORT`,
`SMTP_USERNAME`, `SMTP_PASSWORD`, `FROM_EMAIL`) plus `SMTP_TIMEOUT` and
`SMTP_USE_TLS`. Missing attachment files are skipped and reported in the
structured delivery result instead of failing the whole message.

Example usage after a simulation run:

```python
from app.services.notifications import NotificationService
from app.services.simulation_runner import run_simulation

result = run_simulation({
    "symbol": "EURUSD=X",
    "output_dir": "simulation_output",
    "train_lstm": False,
    "train_rl": False,
})

delivery = NotificationService().notify_simulation_results(
    recipients="trader@example.com",
    simulation_result=result,
)
print(delivery.to_dict())
```

## RL trainer module

`app/services/rl_trainer.py` is the standalone reinforcement-learning training
module.  It owns:

- algorithm selection for `PPO`, `DQN`, `A2C`, and registered `SAC`;
- project defaults plus flat or per-algorithm hyperparameter overrides;
- Stable-Baselines `DummyVecEnv` creation;
- model training with `total_timesteps`;
- model persistence as `.zip` artifacts in the simulation output directory.

`PivotEnv` currently exposes `Discrete(5)` actions, so `PPO`, `DQN`, and `A2C`
can be trained directly. `SAC` is available in the trainer registry, but the
trainer blocks it with a clear validation error until a continuous `Box` action
environment is added.

Example override shape:

```python
from app.services.simulation_runner import run_simulation

result = run_simulation({
    "symbol": "EURUSD=X",
    "train_lstm": False,
    "train_rl": True,
    "rl_algorithm": "PPO",
    "rl_total_timesteps": 10_000,
    "algo_hyperparams": {
        "PPO": {"learning_rate": 0.0001, "n_steps": 512, "batch_size": 64}
    },
    "rl_model_name": "ppo_eurusd_pivot",
})
print(result.model_path)
```
