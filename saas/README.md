# ADC SaaS Platform

This directory is the canonical MVP runtime for the ADC product. The SaaS stack
under `saas/` is the active implementation path for local development,
contract tests, and future deployment work.

The repository still contains notebook/root-level legacy material from the
original research workflow. Treat that layer as an archive and reference only:
do not use it as the backend entry point for MVP runtime changes.

## High-level structure

```text
saas/
├── apps/
│   ├── api/        # FastAPI backend, domain services, jobs, DB access
│   └── web/        # Vite React frontend and frontend feature modules
├── packages/       # Shared contracts, UI primitives, and config
├── infra/          # Deployment, proxy, and infrastructure definitions
├── docs/           # Architecture decisions, API notes, runbooks
└── scripts/        # Developer and CI utility scripts
```

## MVP runtime scope

The current MVP direction is a SaaS web application backed by FastAPI and a Vite
frontend. Runtime work should stay within this stack unless a later PR explicitly
changes the architecture.

Core MVP backend endpoint families live under the versioned `/api/v1` namespace:

- authentication and current-user profile routes;
- dashboard metrics and curves;
- user settings and strategy parameter metadata;
- signal and trade persistence;
- market data, indicator calculation, simulation, RL, and LSTM jobs;
- broker/order/session orchestration, market streaming, notifications, and
  trade-journal import/export.

Readiness, health, and demo-oriented endpoints remain in place for compatibility
and smoke testing, but they are not a separate runtime direction.

## Local environment

Create a local environment file from the SaaS template:

```bash
cd saas
cp .env.example .env
```

The Vite frontend reads the API base URL from `VITE_API_URL`. For local MVP
runs, keep it pointed at the versioned backend namespace:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

Do not use the old `NEXT_PUBLIC_API_BASE_URL` key for this Vite app.

## Canonical local run flow

Run the backend API from the repository root with:

```bash
cd saas/apps/api && uvicorn app.main:app --reload
```

In a second terminal, run the frontend:

```bash
cd saas/apps/web && npm run dev
```

The backend should be reachable at `http://localhost:8000/api/v1`, and the Vite
dev server should use that same base URL via `VITE_API_URL`.

## Validation

Backend contract check:

```bash
cd saas/apps/api && python -m pytest tests/test_api_contracts.py
```

Frontend production build:

```bash
cd saas/apps/web && npm run build
```
