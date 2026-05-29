# Contracts Package

Shared API and event contracts between backend services and frontend clients.

## Current contract owners

- **Backend source of truth:** Pydantic request/response schemas in
  `apps/api/app/schemas/`, grouped by API resource (`auth`, `dashboard`,
  `settings`, `signals`, and `trades`). FastAPI builds the OpenAPI document from
  those models and the route declarations.
- **Frontend consumer view:** `apps/web/src/types/index.ts` mirrors the backend
  schema names and field shapes for the currently implemented API surface.
- **Shared package placeholder:** this package is reserved for generated or
  manually curated API/event contracts once the monorepo has package build and
  publish wiring.

## Contract strategy

The preferred long-term flow is generated contracts:

1. Treat backend Pydantic schemas and FastAPI route response models as the
   canonical API contract.
2. Export the FastAPI OpenAPI document in CI whenever backend schema or endpoint
   files change.
3. Generate TypeScript types from that OpenAPI document into this package.
4. Import generated types from `packages/contracts` in `apps/web` instead of
   hand-maintaining frontend API shapes.

Until generation is wired, keep `apps/web/src/types/index.ts` aligned manually
with the backend schema modules. Manual edits should use the backend Pydantic
class name where practical and include compatibility aliases only when needed by
existing frontend components.

## Proposed package layout

```text
packages/contracts/
  openapi/
    adc-api.v1.json        # generated FastAPI OpenAPI document
  src/
    api.ts                 # generated TypeScript request/response types
    events.ts              # shared domain event types, when introduced
    index.ts               # public exports
```

## Change checklist

When adding or changing an API contract:

1. Update or add the backend schema in the owning resource module under
   `apps/api/app/schemas/`.
2. Ensure the endpoint declares the correct request body, response model, and
   status code so OpenAPI reflects the runtime contract.
3. Update frontend types manually in `apps/web/src/types/index.ts` until the
   generated package is available.
4. Add or update API tests that serialize representative payloads.
5. Regenerate OpenAPI and TypeScript contracts once generation is enabled.
