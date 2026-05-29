# API Documentation

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

```text
GET http://localhost:8000/api/v1/health
```

## Proxy and deployment assumptions

Frontend deployments should pass `VITE_API_URL` with the complete versioned base
URL. Reverse proxies may match `/api` as a broad upstream prefix, but the routed
application endpoints should continue to be requested under `/api/v1`.
