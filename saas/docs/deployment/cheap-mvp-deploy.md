# Cheap MVP deployment guide

This guide documents the smallest production-shaped deployment contract for the
ADC SaaS MVP. It intentionally favors managed platform defaults over custom
infrastructure so the MVP can run on Render or Railway for the FastAPI backend,
managed Postgres for persistence, and Vercel or another static host for the Vite
frontend.

## Target topology

```text
Browser
  -> Vercel/static frontend (Vite build)
  -> Render/Railway backend (FastAPI, /api/v1)
  -> Managed Postgres
```

Redis, Celery workers, Terraform, and Nginx are not required for the cheap MVP
request path. Add them later only when background training, scheduled jobs,
custom networking, or reverse-proxy requirements justify the extra moving parts.

## Required environment contract

### Backend

Set these variables in Render/Railway for the API service:

| Variable | Required | Example | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | Yes | `production` | Identifies the hosted environment. |
| `APP_NAME` | Yes | `ADC Trading Platform` | Display/config name. |
| `DATABASE_URL` | Yes | `postgresql://user:pass@host:5432/db` | Use the managed Postgres connection string. |
| `SECRET_KEY` | Yes | generated secret | Use a strong per-environment value. |
| `CORS_ORIGINS` | Yes | `["https://adc-web.vercel.app"]` | JSON list of frontend origins allowed to call the API. |
| `MARKET_DATA_PROVIDER` | Yes | `yahoo` | Use `mock` for demo/offline environments. |
| `BROKER_PROVIDER` | Yes | `mock` | MVP-safe default; do not connect live brokers by default. |
| `AI_PROVIDER` | Yes | `mock` | Keeps the cheap MVP independent of paid AI providers. |

Optional/lab backend variables:

| Variable | When to set |
| --- | --- |
| `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Override JWT defaults. |
| `ALPHA_VANTAGE_API_KEY` | Enable Alpha Vantage market data. |
| `REDIS_URL` | Enable Redis-backed Celery or other async features. |
| `SMTP_*`, `FROM_EMAIL` | Enable outbound email notifications. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Enable billing experiments. |

`PORT` is supplied by Render/Railway at runtime. The application code does not
need a `PORT` setting; pass it to Uvicorn in the deploy start command.

### Frontend

Set this build-time variable in Vercel/static hosting:

```env
VITE_API_URL=https://<backend-domain>/api/v1
```

Rebuild the frontend after changing `VITE_API_URL`; Vite embeds this value at
build time.

## Render backend quick setup

1. Create a managed Postgres database and copy its internal/external
   `DATABASE_URL` for the API service.
2. Create a Web Service from the repository.
3. Set the root directory to `saas/apps/api`.
4. Use the build command:

   ```bash
   pip install --upgrade pip && pip install .
   ```

5. Use the start command:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

6. Add the backend environment variables from the contract above.
7. After the frontend is deployed, set `CORS_ORIGINS` to include the exact
   frontend origin, for example:

   ```env
   CORS_ORIGINS=["https://adc-web.vercel.app"]
   ```

## Railway backend quick setup

1. Create a Railway project with a Postgres service.
2. Add a backend service from the repository and set the service root to
   `saas/apps/api`.
3. Use the install/build command:

   ```bash
   pip install --upgrade pip && pip install .
   ```

4. Use the start command:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

5. Set `DATABASE_URL` from the Railway Postgres service reference and add the
   remaining backend environment variables.

## Vercel/static frontend quick setup

1. Create a frontend project from the repository.
2. Set the root directory to `saas/apps/web`.
3. Use the install command supported by the host, typically `npm install`.
4. Use the build command:

   ```bash
   npm run build
   ```

5. Publish the generated `dist` directory.
6. Set the frontend build-time environment variable:

   ```env
   VITE_API_URL=https://<backend-domain>/api/v1
   ```

7. Add the deployed frontend origin to backend `CORS_ORIGINS` and redeploy the
   backend if the provider does not apply environment changes automatically.

## Local commands remain unchanged

Local development should continue to use the existing commands:

```bash
cd saas/apps/api && uvicorn app.main:app --reload
cd saas/apps/web && npm run dev
```

The hosted backend differs only in its start command, where the platform-provided
`PORT` is forwarded to Uvicorn.

## Post-deploy smoke checks

Use the versioned API base path in every check:

```bash
curl --fail https://<backend-domain>/api/v1/health
```

From a local checkout, keep running the same MVP validation commands before
shipping deployment changes:

```bash
cd saas && docker compose config
cd saas/apps/api && python -m pytest tests/test_api_contracts.py
cd saas/apps/web && npm run build
```
