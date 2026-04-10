# Architecture Overview

This document describes the implemented Winoe backend architecture as of March 27, 2026.

## Runtime Composition

- Entry points: `app/api/main.py` (primary) and `app/main.py` (deployment shim).
- Application assembly: `app/shared/http/shared_http_app_builder_service.py`.
- Router registration: `app/shared/http/shared_http_router_registry_service.py`.
- Middleware stack:
  - CORS and CSRF origin enforcement
  - request body size limits
  - trusted proxy header handling
  - optional performance instrumentation (`WINOE_DEBUG_PERF`, `WINOE_PERF_*`)

## Domain Modules

- `app/trials/*`: trial lifecycle, invites, scenario versioning, candidate compare payloads.
- `app/candidates/*`: candidate session resolve/claim/schedule/current-task/privacy flows.
- `app/tasks/*`: candidate execution routes (codespace/run/submit/draft/handoff upload/status).
- `app/submissions/*`: submission persistence, talent_partner list/detail presenters, workspace orchestration.
- `app/evaluations/*`: winoe-report API, evaluator pipeline, run/day-score lifecycle.
- `app/media/*`: recording/transcript repositories and privacy retention controls.
- `app/talent_partners/*`: admin template checks and demo admin operations.
- `app/shared/*`: auth, database/session wiring, durable jobs, logging, perf, and cross-cutting utils.

## Integration Boundaries

- GitHub integration (`app/integrations/github/*`):
  - API transport/client operations
  - Actions run dispatch/polling
  - artifact parsing and webhook handling
  - template health checks
- Email providers (`app/integrations/email/email_provider/*`): console/resend/sendgrid/smtp.
- Storage media providers (`app/integrations/storage_media/*`): recording upload/status/delete paths.

## Data and Persistence

- SQLAlchemy ORM models are centralized through `app/shared/database/shared_database_models_model.py`.
- Migrations: `alembic/versions/*`.
- Async DB session provider: `app/shared/database/__init__.py`.
- Domain repositories keep query/mutation logic colocated with domain packages.

## Auth and Access Model

- Principal extraction: `app/shared/auth/principal/*`.
- Talent Partner/candidate route guards are dependency-driven.
- Admin template endpoints require `X-Admin-Key`.
- Demo admin operations require demo-mode admin dependency resolution.

## Async Jobs and Side Effects

- Durable jobs table/model in `app/shared/jobs/repositories/*`.
- Worker handlers in `app/shared/jobs/handlers/*`.
- Key job types include:
  - scenario generation
  - evaluation run
  - day-close enforcement/finalization
  - transcription
  - workspace/trial cleanup

## Documentation Sources of Truth

- API schema truth: `code-quality/documentation/latest/artifacts/openapi_snapshot.json`.
- Endpoint matrix truth: `code-quality/documentation/latest/artifacts/api_endpoint_matrix.md`.
- Environment parity truth: `code-quality/documentation/latest/artifacts/env_inventory.md`.
- Docstring coverage truth: `code-quality/documentation/latest/artifacts/docstring_audit.json`.
