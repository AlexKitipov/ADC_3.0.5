# MVP Release Checklist

This checklist is the final acceptance gate for the ADC SaaS MVP. It does not introduce new product scope; it captures the smoke commands and manual verification steps that must pass before an MVP release candidate is promoted.

## Release candidate scope

The MVP release candidate is accepted when these user journeys work together against the same backend and frontend build:

- Authentication: register a new user and log in with the new credentials.
- Settings: load default user settings and save updated settings.
- Signals: generate or create a signal, then read latest signals and symbol-specific signal history.
- Trades: open a trade, view it in trade history, close it, and verify the status is updated.
- Dashboard: confirm metrics and charts reflect the latest smoke data after settings, signals, and trades change.
- Deployment: validate Docker Compose configuration and keep the cheap MVP deployment guide current.

## Local automated smoke commands

Run these commands from a clean checkout before tagging or deploying an MVP release candidate:

```bash
cd saas/apps/api && python -m pytest
cd saas/apps/web && npm test -- --run
cd saas/apps/web && npm run build
cd saas && docker compose config
```

Equivalent Make targets are available from `saas/`:

```bash
make test-api
make test-web
make build-web
make compose-config
```

## Docker-backed API smoke

The API smoke script exercises the core backend MVP contract against a running API. Start the stack first, then run the smoke target:

```bash
cd saas && docker compose up --build
cd saas && make smoke-api
```

By default, `make smoke-api` calls `scripts/smoke-api.sh` against `http://localhost:8000/api/v1`. Override the target API with `API_URL` when testing another environment:

```bash
cd saas && API_URL=https://api.example.com/api/v1 make smoke-api
```

The script validates:

1. Health endpoint responds.
2. User registration succeeds.
3. Login returns an access token.
4. Default user settings can be read.
5. User settings can be updated.
6. Signals can be created and queried.
7. Dashboard stats and chart data can be read.
8. Public readiness placeholder routes respond.

## Manual acceptance checklist

Complete this manual pass in the browser against the same API/database used for smoke testing:

- [ ] Register a new user.
- [ ] Log in with that user.
- [ ] Open settings and confirm defaults are visible.
- [ ] Save updated settings and refresh to confirm persistence.
- [ ] Generate or create a trading signal.
- [ ] Confirm latest signals update in the UI.
- [ ] Open a trade from the MVP trading flow.
- [ ] Confirm the trade appears in trade history.
- [ ] Close the trade.
- [ ] Confirm dashboard metrics update after the trade is closed.

## Release decision

The MVP release candidate is ready when all automated commands pass, `make smoke-api` passes against the intended environment, and every manual acceptance checkbox is complete. If a failure is discovered, fix only the smallest contract or documentation mismatch needed for this release gate and rerun the full checklist.
