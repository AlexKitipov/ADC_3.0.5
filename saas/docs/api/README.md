# ADC API Documentation

The canonical frontend-facing REST API base path is `/api/v1`.

Use this versioned prefix for all browser clients, integration tests, deployment
configuration, and reverse-proxy rules. Unversioned `/api/*` resource routes are
not registered, which keeps endpoint ownership clear as future API versions are
introduced.

## Local base URL

When running the default local stack, the API is available at:

```text
http://localhost:8000/api/v1
```

Health checks use the same versioned namespace:

```http
GET /api/v1/health
```

## Authentication requirements

The API uses JWT bearer authentication. Obtain a token with
`POST /api/v1/auth/login`, then send it on protected requests:

```http
Authorization: Bearer <access_token>
```

FastAPI exposes this as the `OAuth2PasswordBearer` security scheme. The login
route accepts `application/x-www-form-urlencoded` fields named `username` and
`password`; JSON login bodies are not part of the contract.

Public/readiness endpoints are intentionally unauthenticated:

- `GET /api/v1/health`
- `GET /auth/status`
- placeholder/readiness collection endpoints such as `GET /signals`,
  `GET /trades`, `GET /settings`, `GET /dashboard/summary`
- stateless computation/data helpers: `GET /market-data/ohlcv`,
  `POST /indicators/calculate`, and `GET /strategy/parameters`

All user-specific or stateful routes require `Authorization: Bearer <token>`.
This includes `/auth/me`, dashboard metrics, settings, signal creation, trade
state, order management, sessions, simulations, RL/LSTM jobs, notifications, and
trade-journal operations.

## Contract validation

The executable integration contract is maintained in
`saas/apps/api/tests/test_api_contracts.py`. It statically validates that:

1. the backend registers the expected route set under the canonical `/api/v1`
   base path;
2. frontend API modules only consume routes that exist in the backend contract;
3. frontend default base URLs include `/api/v1`;
4. this documentation covers every endpoint family and the authentication
   scheme.

Run it with the backend tests:

```bash
cd saas/apps/api
python -m pytest tests/test_api_contracts.py
```

FastAPI also exposes generated OpenAPI at runtime:

- JSON schema: `GET /openapi.json`
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`


## MVP vs Advanced/Lab endpoint families

The MVP SaaS shell exposes the stable navigation surface for Dashboard,
Signals, Trades/History, and Settings. The backend still registers the
following Advanced/Lab endpoint families so direct URLs, experiments, and
integration tests keep working, but they are not part of the primary MVP
navigation contract:

- `/rl`
- `/lstm`
- `/simulations`
- `/sessions`
- `/trade-journal`
- `/notifications`
- `/market-stream`

These Advanced/Lab routes are intended for research, runtime operations,
delivery diagnostics, generated artifacts, and streaming workflows. They must
remain documented and routable even when the frontend hides lab links behind a
feature flag.

## Endpoint reference

All paths below are relative to `/api/v1`.

### Auth

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/auth/status` | Public | Authentication service readiness. |
| `POST` | `/auth/register` | Public | Create a user account with a unique email and username. |
| `POST` | `/auth/login` | Public | Exchange username/password form fields for a bearer token. |
| `GET` | `/auth/me` | Bearer | Return the current user's public profile. |

Register request:

```json
{
  "email": "alice@example.com",
  "username": "alice",
  "password": "correct-horse-battery-staple"
}
```

Login request (`application/x-www-form-urlencoded`):

```text
username=alice&password=correct-horse-battery-staple
```

Token response:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

### Dashboard

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/dashboard/summary` | Public | Dashboard service readiness. |
| `GET` | `/dashboard/stats` | Bearer | Aggregated balance, equity, drawdown, win-rate, trade count, and monthly PnL. |
| `GET` | `/dashboard/equity-curve?days=30` | Bearer | Equity and balance snapshots for the lookback window. |
| `GET` | `/dashboard/drawdown-curve?days=30` | Bearer | Drawdown snapshots for the lookback window. |

Stats response example:

```json
{
  "total_balance": 10000,
  "current_equity": 10250,
  "max_drawdown": 0.04,
  "win_rate": 0.58,
  "total_trades": 42,
  "monthly_pnl": 250
}
```

### Settings

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/settings` | Public | Settings service readiness. |
| `GET` | `/settings/user-settings` | Bearer | Read the current user's trading settings, creating defaults when absent. |
| `PUT` | `/settings/user-settings` | Bearer | Replace the current user's trading settings. |

Update request:

```json
{
  "symbols": ["BTCUSD", "ETHUSD"],
  "timeframe": "1h",
  "balance": 10000,
  "risk_per_trade": 0.02,
  "grid_levels": 5,
  "grid_step_pct": 0.005,
  "martingale_factor": 1.5,
  "enable_trading": false,
  "email_notifications": true
}
```

### Signals

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/signals` | Public | Signal collection readiness payload. |
| `POST` | `/signals/create` | Bearer | Persist a generated signal for the current user. |
| `GET` | `/signals/latest?limit=10` | Bearer | Return the newest signals for the current user. |
| `GET` | `/signals/by-symbol/{symbol}?limit=20` | Bearer | Return signals for a symbol. |

Create request:

```json
{
  "symbol": "BTCUSD",
  "action": "BUY",
  "price": 68420.5,
  "rsi": 54.2,
  "macd": 1.7
}
```

### Trades

These endpoints manage simple user-visible trade records; broker/order
submission is handled by the orders API.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/trades` | Public | Trade collection readiness payload. |
| `POST` | `/trades/open` | Bearer | Create an open trade record. |
| `POST` | `/trades/close/{trade_id}` | Bearer | Close a trade and calculate PnL. |
| `GET` | `/trades/open` | Bearer | List open trades. |
| `GET` | `/trades/closed?limit=50` | Bearer | List recently closed trades. |

Open request:

```json
{
  "symbol": "BTCUSD",
  "entry_price": 68420.5
}
```

Close request:

```json
{
  "exit_price": 69000
}
```

### Strategy parameters

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/strategy/parameters` | Public | Return metadata for supported simulation and strategy form fields. |

Response item example:

```json
{
  "name": "grid_levels",
  "group": "pivot_grid",
  "label": "Grid Levels",
  "default": 3,
  "min_value": 1,
  "max_value": 20,
  "step": 1,
  "options": [],
  "description": "Number of grid levels above and below pivot prices."
}
```

### Simulation

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/simulations` | Bearer | Start a simulation run. |
| `GET` | `/simulations/{simulation_id}` | Bearer | Read run status, parameters, result, or error. |
| `GET` | `/simulations/{simulation_id}/artifacts` | Bearer | List generated artifacts for a run. |

Create request:

```json
{
  "symbol": "EURUSD=X",
  "timeframe": "1d",
  "start_date": "2024-01-01",
  "end_date": "2024-06-01",
  "train_lstm": false,
  "train_rl": false,
  "save_charts": false,
  "initial_balance": 10000,
  "grid_levels": 3,
  "grid_step_pct": 0.005
}
```

Run response excerpt:

```json
{
  "id": "sim-123",
  "status": "completed",
  "created_at": "2026-01-02T12:00:00Z",
  "completed_at": "2026-01-02T12:01:00Z",
  "parameters": { "symbol": "EURUSD=X" },
  "result": {
    "output_dir": "simulation_output",
    "total_steps": 120,
    "trained_lstm": false,
    "trained_rl": false,
    "performance": { "total_return": 0.03 }
  },
  "error": null
}
```

### Market data

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/market-data/ohlcv` | Public | Fetch OHLCV rows for `symbol`, `timeframe`, and optional date bounds. |

Example:

```http
GET /api/v1/market-data/ohlcv?symbol=AAPL&timeframe=1d&start_date=2024-01-01&end_date=2024-02-01
```

Supported timeframe values are `1d`, `1min`, `5min`, `15min`, `30min`, and
`60min`.

### Indicators

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/indicators/calculate` | Public | Calculate RSI, MACD, Bollinger Bands, ATR, pivot levels, and RSI crosses for supplied OHLCV rows. |

Request:

```json
{
  "rows": [
    {
      "timestamp": "2026-01-02T00:00:00Z",
      "symbol": "AAPL",
      "open": 100,
      "high": 102,
      "low": 99,
      "close": 101,
      "volume": 1000
    }
  ],
  "parameters": {
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bollinger_period": 20,
    "bollinger_std": 2,
    "atr_period": 14
  }
}
```

### RL

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/rl/train` | Bearer | Start a reinforcement-learning training job. |
| `GET` | `/rl/jobs/{job_id}` | Bearer | Read RL job status/result/error. |
| `GET` | `/rl/models/{model_id}` | Bearer | Read saved RL model artifact metadata. |

Training request:

```json
{
  "algorithm": "PPO",
  "total_timesteps": 10000,
  "environment": "pivot-grid",
  "symbol": "EURUSD=X",
  "timeframe": "1d",
  "initial_balance": 10000,
  "grid_levels": 3,
  "grid_step_pct": 0.005,
  "save_model": true,
  "model_name": "ppo_eurusd_pivot"
}
```

Supported algorithms are `PPO`, `DQN`, `A2C`, and registered `SAC`; `SAC` is
blocked by the trainer until a continuous action environment is introduced.

### LSTM

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/lstm/train` | Bearer | Start an LSTM training job from OHLCV rows. |
| `POST` | `/lstm/generate` | Bearer | Generate synthetic candles from a completed LSTM job. |
| `GET` | `/lstm/jobs/{job_id}` | Bearer | Read LSTM job status/result/error. |

Training request:

```json
{
  "rows": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "symbol": "MSFT",
      "open": 100,
      "high": 101,
      "low": 99,
      "close": 100.5,
      "volume": 1000
    }
  ],
  "features": ["Open", "High", "Low", "Close", "Volume"],
  "sequence_length": 2,
  "epochs": 1,
  "batch_size": 2
}
```

Generate request:

```json
{
  "job_id": "lstm-job-123",
  "num_steps": 25,
  "seed_rows": null
}
```

### Orders

These endpoints represent simulated/broker order-management operations and are
separate from simple trade journal records.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/orders` | Bearer | Create an order. |
| `GET` | `/orders/open` | Bearer | List currently open orders. |
| `GET` | `/orders/{ticket}` | Bearer | Read one order by broker ticket. |
| `POST` | `/orders/{ticket}/close` | Bearer | Close all or part of an order. |

Create request:

```json
{
  "symbol": "EURUSD",
  "order_type": "BUY",
  "volume": 0.1,
  "price": 1.085,
  "stop_loss": 1.08,
  "take_profit": 1.095,
  "slippage": 3,
  "comment": "api example",
  "magic": 10001
}
```

Close request:

```json
{
  "volume": 0.1,
  "price": 1.09,
  "slippage": 3,
  "exit_reason": "target"
}
```

### Sessions

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/sessions` | Bearer | Create a trading session, optionally auto-starting it. |
| `GET` | `/sessions/current` | Bearer | Read the current session for the user. |
| `POST` | `/sessions/{session_id}/start` | Bearer | Start a created/stopped session. |
| `POST` | `/sessions/{session_id}/stop` | Bearer | Stop a running session. |
| `GET` | `/sessions/{session_id}/events?limit=100` | Bearer | List recent session events. |

Create request:

```json
{
  "auto_start": true,
  "config": {
    "symbol": "EURUSD",
    "initial_price": 1.085,
    "price_volatility": 0.001,
    "stream_interval": 1,
    "order_volume": 0.1,
    "slippage": 3,
    "broker_trade_allowed": true,
    "retry_attempts": 3,
    "random_seed": 42
  }
}
```

### Market stream

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/market-stream/{symbol}?interval=1&max_ticks=` | Public | Server-sent events stream for market ticks. |

The endpoint emits SSE events. Browser clients should use `EventSource` against
the same `/api/v1` base URL. `tick` events contain `MarketTick` JSON:

```json
{
  "symbol": "BTCUSD",
  "price": 68420.5,
  "bid": 68420.0,
  "ask": 68421.0,
  "timestamp": "2026-01-02T12:00:00Z"
}
```

### Notifications

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/notifications/test` | Bearer | Send a test email notification, optionally with attachments. |
| `POST` | `/notifications/simulation-results` | Bearer | Send simulation result email with result-derived and extra attachments. |

Test request:

```json
{
  "recipients": ["trader@example.com"],
  "subject": "ADC notification test",
  "body": "Delivery check",
  "attachments": [
    {
      "path": "simulation_output/report.csv",
      "filename": "report.csv",
      "content_type": "text/csv"
    }
  ]
}
```

Delivery response:

```json
{
  "status": "sent",
  "recipients": ["trader@example.com"],
  "subject": "ADC notification test",
  "attached_files": ["report.csv"],
  "skipped_attachments": [],
  "error": null
}
```

### Trade journal

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/trade-journal?output_dir=simulation_output&suffix=v2` | Bearer | Browse journal artifacts and related persisted trade counts. |
| `GET` | `/trade-journal/{entry_id}` | Bearer | Read one normalized journal entry. |
| `POST` | `/trade-journal/import?artifact_type=trades` | Bearer | Import a CSV/JSON artifact via multipart form field `file`. |
| `GET` | `/trade-journal/export?download=false` | Bearer | Create and return archive metadata. |
| `GET` | `/trade-journal/export?download=true` | Bearer | Download the generated archive as `application/zip`. |

Import request uses `multipart/form-data`:

```text
file=@trades.csv; artifact_type=trades
```

Summary response excerpt:

```json
{
  "entries": [],
  "artifacts": [
    {
      "name": "trades.csv",
      "artifact_type": "trades",
      "path": "simulation_output/journal/trades.csv",
      "exists": true,
      "size_bytes": 2048,
      "modified_at": "2026-01-02T12:00:00Z",
      "row_count": 12,
      "content_type": "text/csv"
    }
  ],
  "db_trade_count": 12,
  "open_db_trade_count": 2,
  "closed_db_trade_count": 10,
  "relationships": {
    "persisted_trade_rows": "Trades persisted through /trades endpoints.",
    "broker_order_records": "Orders managed through /orders endpoints.",
    "journal_artifacts": "Simulation/import artifacts exposed for audit and export."
  }
}
```

## Proxy and deployment assumptions

Frontend deployments should pass `VITE_API_URL` with the complete versioned base
URL. Reverse proxies may match `/api` as a broad upstream prefix, but the routed
application endpoints should continue to be requested under `/api/v1`.
