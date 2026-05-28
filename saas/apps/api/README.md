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
