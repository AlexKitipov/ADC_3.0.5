# Infrastructure

Deployment and local infrastructure definitions for ADC SaaS.

## Current MVP deployment path

Use the cheap managed-platform deployment guide for the current MVP:

- [Cheap MVP deployment guide](../docs/deployment/cheap-mvp-deploy.md)

The production-shaped MVP target is:

- Render or Railway for the FastAPI backend;
- managed Postgres for persistence;
- Vercel or another static host for the Vite frontend;
- optional Redis/Celery only when background workers are enabled.

## Future infrastructure

The `terraform/` and `nginx/` directories are placeholders for future needs.
They are not required for the cheap MVP deploy and should not block deploying the
current Render/Railway + managed Postgres + Vercel/static topology.

Keep local Docker assets focused on development and smoke testing unless a later
PR explicitly promotes them to production infrastructure.
