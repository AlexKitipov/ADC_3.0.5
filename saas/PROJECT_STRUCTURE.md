# Project Structure

## `apps/api`

Backend service boundaries:

- `app/api/v1/endpoints` - HTTP route modules grouped by API resource.
- `app/core` - application settings, security helpers, logging, and shared framework setup.
- `app/db` - database session setup, migrations, and repository abstractions.
- `app/models` - persistence models.
- `app/schemas` - request/response and internal DTO schemas.
- `app/services` - business use cases for strategies, experiments, billing, and analytics.
- `app/workers` - background jobs for market data, metrics, and notifications.
- `tests` - API and unit tests for backend behavior.

## `apps/web`

Frontend service boundaries:

- `src/app` - route groups and page shells.
- `src/components` - shared layout and UI components.
- `src/features` - product modules such as auth, trading, analytics, and billing.
- `src/hooks` - reusable frontend hooks.
- `src/lib` - client helpers and shared utilities.
- `src/styles` - global styles and design tokens.
- `src/types` - frontend TypeScript types.

## `packages`

Shared workspace packages:

- `contracts` - API/event contract definitions shared between services.
- `config` - linting, formatting, and build configuration presets.
- `ui` - reusable UI primitives intended for the web app.

## `infra`

Operations assets:

- `docker` - container build/development helpers.
- `nginx` - reverse proxy configuration.
- `terraform` - infrastructure-as-code modules and environment definitions.

## `docs`

Project knowledge base:

- `adr` - architecture decision records.
- `api` - public/internal API documentation.
- `architecture` - diagrams and system design notes.
- `runbooks` - operational procedures.
