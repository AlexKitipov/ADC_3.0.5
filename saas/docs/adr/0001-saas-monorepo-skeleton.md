# ADR 0001: SaaS monorepo skeleton

## Status

Accepted

## Context

The repository currently contains a research notebook and archive-oriented documentation for ADC forex strategy experimentation. The SaaS product needs a separate, incremental implementation area where backend, frontend, shared packages, infrastructure, and documentation can evolve through focused pull requests.

## Decision

Create a `saas` monorepo skeleton with:

- `apps/api` for the backend service
- `apps/web` for the frontend application
- `packages` for shared contracts, configuration, and UI primitives
- `infra` for deployment assets
- `docs` for architecture and operational knowledge

## Consequences

- Follow-up pull requests can add production code without mixing concerns.
- The existing notebook remains untouched as the historical/research artifact.
- Teams can review backend, frontend, and infrastructure changes independently.
