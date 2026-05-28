# API App

Python backend application for ADC SaaS.

Implemented responsibilities:

- FastAPI application entry point in `app/main.py`
- REST API endpoints under `/api/v1`
- Health checks at `/api/health` and `/api/v1/health`
- SQLAlchemy engine/session setup
- Celery application setup backed by Redis
- Environment-driven configuration for database, Redis, JWT, and SMTP settings

Planned responsibilities:

- Authentication and account management
- Strategy archive and experiment management
- Market data ingestion orchestration
- Backtesting/metrics services
- Background worker entry points

## Local development

Copy the example environment from the SaaS root before running the stack:

```bash
cp ../../.env.example ../../.env
```

Run the API from this directory:

```bash
uvicorn app.main:app --reload
```

Run the smoke tests:

```bash
pytest
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
