# Nginx

Reverse proxy configuration will be added here.

When a proxy is introduced, it should preserve `/api/v1` as the canonical API
base path and forward those requests to the backend service. A broader `/api`
location may be useful for matching traffic, but frontend-facing routes should
not depend on unversioned `/api/*` backend endpoints.
