# Docker

Container build helpers and development Docker assets.


## MVP compose runtime

The default `saas/docker-compose.yml` path is intentionally a single FastAPI service
plus Postgres and the Vite web app. Redis and the Celery worker are optional
background/lab services behind the `worker` profile, so the backend can start for
MVP deploys without Redis, Celery, RL, or LSTM dependencies in the critical path.

Use the worker profile only when background jobs are needed:

```bash
cd saas
docker compose --profile worker up --build celery
```
