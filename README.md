# Winoe Backend

FastAPI + PostgreSQL backend for Winoe's async trial platform. Talent Partners create and manage trials, candidates complete session tasks, and GitHub-native workflows capture code/debug execution artifacts for talent_partner review.

## Overview

- Domain modules: trials, candidate sessions, tasks, submissions, evaluations, media, notifications, talent_partners/admin, and shared runtime infrastructure.
- GitHub-native flow: empty-repo workspace provisioning, Codespaces init/status, Actions evidence capture, artifact parsing, and persisted run/test metadata.
- Auth model: bearer-token principal model with talent_partner/candidate permission gates, plus admin key and demo admin dependency paths.
- Current API surface: 57 HTTP endpoints (generated from live OpenAPI).

## Stack (Poetry Constraints)

| Component | Version Constraint |
|---|---|
| Python | `^3.11` |
| FastAPI | `^0.109.0` |
| Uvicorn | `^0.27.0` (`standard` extras) |
| SQLAlchemy | `^2.0.25` |
| asyncpg | `^0.29.0` |
| psycopg2-binary | `^2.9.9` |
| Alembic | `^1.13.1` |
| pydantic-settings | `^2.1.0` |
| python-jose (`cryptography`) | `^3.5.0` |
| python-dotenv | `^1.0.0` |
| email-validator | `^2.3.0` |
| greenlet | `^3.3.0` |

Dev/test tools: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, `ruff`, `black`, `hypothesis`, `aiosqlite`.

## Prerequisites

- Python `3.11+`
- Poetry
- PostgreSQL (for local app runtime and Alembic migrations)
- Optional for QA workflows:
  - Node.js + Newman for API QA runner
  - Local GitHub credentials/token for workspace flows

## Setup

1. Install dependencies.

```bash
poetry install
```

2. Configure local environment values in `.env`.

```bash
# edit .env and set required values for your machine
```

3. Apply database migrations.

```bash
./runBackend.sh migrate
```

4. Bootstrap the local demo seed data if you are starting from a fresh database.

```bash
./runBackend.sh bootstrap-local
```

5. Start API server and worker together for local development.

```bash
./runBackend.sh
```

6. Start API only.

```bash
./runBackend.sh api
```

7. Start worker only.

```bash
./runBackend.sh worker
```

8. Retry dead-letter Winoe jobs after schema repair.

```bash
./runBackend.sh retry-dead-jobs
```

9. Smoke check.

```bash
curl -s http://localhost:8000/health
```

10. Readiness check and local demo smoke test.

```bash
curl -s http://localhost:8000/ready
poetry run python scripts/local_demo_smoke_test.py --base-url http://localhost:8000
```

11. Local QA runtime for claim/invite flows with the supported dev bypass enabled.

```bash
bash scripts/local_qa_backend.sh
```

## Environment

Canonical env keys are summarized below by primary group.

| Group | Primary Keys |
|---|---|
| Core runtime | `WINOE_ENV`, `WINOE_API_PREFIX`, `DEV_AUTH_BYPASS`, `WINOE_DEV_AUTH_BYPASS`, `WINOE_RATE_LIMIT_ENABLED`, `WINOE_MAX_REQUEST_BODY_BYTES` |
| Jobs runtime | `WINOE_WORKER_HEARTBEAT_INTERVAL_SECONDS`, `WINOE_WORKER_HEARTBEAT_STALE_SECONDS` |
| Perf / diagnostics | `WINOE_DEBUG_PERF`, `WINOE_PERF_SPANS_ENABLED`, `WINOE_PERF_SQL_FINGERPRINTS_ENABLED`, `WINOE_PERF_SPAN_SAMPLE_RATE` |
| Demo/admin mode | `WINOE_DEMO_MODE`, `WINOE_SCENARIO_DEMO_MODE`, `WINOE_DEMO_ADMIN_ALLOWLIST_*` |
| Database | `WINOE_DATABASE_URL`, `WINOE_DATABASE_URL_SYNC` |
| Auth0 | `WINOE_AUTH0_*` |
| CORS / CSRF | `WINOE_CORS_ALLOW_*`, `WINOE_CSRF_*` |
| GitHub | `WINOE_GITHUB_*`, `WINOE_WORKSPACE_*` |
| Scenario provider creds | `WINOE_OPENAI_API_KEY`, `WINOE_ANTHROPIC_API_KEY` |
| Media | `WINOE_MEDIA_*`, `WINOE_SIGNED_URL_EXPIRY_SECONDS` |
| Email | `WINOE_EMAIL_PROVIDER`, `WINOE_EMAIL_FROM`, `WINOE_RESEND_API_KEY`, `SENDGRID_API_KEY`, `SMTP_*` |
| Admin key | `WINOE_ADMIN_API_KEY` |

## Project Structure

| Path | Responsibility |
|---|---|
| `app/api/main.py` | App entrypoint wiring and exported `app` |
| `app/shared/http/*` | App builder, middleware, router registry, error handlers |
| `app/config/*` | Environment settings models/validators/merge behavior |
| `app/trials/*` | Trial lifecycle, invites, scenario versions, compare views |
| `app/candidates/*` | Candidate session resolve/claim/schedule/privacy/current-task flows |
| `app/tasks/*` | Codespace/run/submit/draft/handoff route orchestration |
| `app/submissions/*` | Workspace provisioning, run persistence, talent_partner presentation |
| `app/evaluations/*` | Winoe Report API, evaluators, evaluation repositories |
| `app/media/*` | Recording/transcript storage + privacy services |
| `app/talent_partners/*` | Talent Partner admin and demo admin operations |
| `app/shared/jobs/*` | Durable job models, handlers, worker services |
| `alembic/` | DB migrations |
| `docs/` | Canonical architecture/API documentation |
| `qa_verifications/` | QA runner scripts and latest generated QA reports |
| `scripts/` | Operational tooling, docs audits/exports |

## API Overview (57 Endpoints)

### Health / Auth

- `GET /health`
- `GET /ready`
- `POST /api/auth/talent-partner-onboarding`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Admin Templates / Demo Admin Ops

- `POST /api/admin/candidate_sessions/{candidate_session_id}/day_windows/control`
- `POST /api/admin/candidate_sessions/{candidate_session_id}/reset`
- `POST /api/admin/jobs/{job_id}/requeue`
- `POST /api/admin/trials/{trial_id}/scenario/use_fallback`
- `POST /api/admin/media/purge`

### Talent Partner Trial + Submission APIs

- `GET /api/trials`
- `POST /api/trials`
- `GET /api/trials/{trial_id}`
- `PUT /api/trials/{trial_id}`
- `POST /api/trials/{trial_id}/invite`
- `POST /api/trials/{trial_id}/candidates/{candidate_session_id}/invite/resend`
- `GET /api/trials/{trial_id}/candidates`
- `GET /api/trials/{trial_id}/candidates/compare`
- `POST /api/trials/{trial_id}/activate`
- `POST /api/trials/{trial_id}/terminate`
- `POST /api/trials/{trial_id}/scenario/regenerate`
- `POST /api/trials/{trial_id}/scenario/{scenario_version_id}/approve`
- `PATCH /api/trials/{trial_id}/scenario/active`
- `PATCH /api/trials/{trial_id}/scenario/{scenario_version_id}`
- `GET /api/submissions`
- `GET /api/submissions/{submission_id}`
- `GET /api/candidate_sessions/{candidate_session_id}/winoe_report`
- `POST /api/candidate_sessions/{candidate_session_id}/winoe_report/generate`

### Candidate Session APIs

- `GET /api/candidate/session/{token}`
- `POST /api/candidate/session/{token}/claim`
- `POST /api/candidate/session/{token}/schedule`
- `GET /api/candidate/session/{token}/review`
- `GET /api/candidate/session/{candidate_session_id}/current_task`
- `GET /api/candidate/invites`
- `POST /api/candidate/session/{candidate_session_id}/privacy/consent`

### Company Config / Media Storage

- `GET /api/companies/me/ai-config`
- `PUT /api/companies/me/ai-config`
- `GET /api/recordings/storage/fake/download`
- `PUT /api/recordings/storage/fake/upload`

### Candidate Task Execution / Draft / Handoff APIs

- `POST /api/tasks/{task_id}/codespace/init`
- `GET /api/tasks/{task_id}/codespace/status`
- `POST /api/tasks/{task_id}/run`
- `GET /api/tasks/{task_id}/run/{run_id}`
- `POST /api/tasks/{task_id}/submit`
- `GET /api/tasks/{task_id}/draft`
- `PUT /api/tasks/{task_id}/draft`
- `POST /api/tasks/{task_id}/presentation/upload/init`
- `POST /api/tasks/{task_id}/presentation/upload/complete`
- `GET /api/tasks/{task_id}/presentation/upload/status`
- `POST /api/tasks/{task_id}/handoff/upload/init`
- `POST /api/tasks/{task_id}/handoff/upload/complete`
- `GET /api/tasks/{task_id}/handoff/status`
- `POST /api/recordings/{recording_id}/delete`

### Webhooks / Jobs

- `POST /api/github/webhooks`
- `GET /api/jobs/{job_id}`

Detailed schema-level API docs are generated at [`docs/api.md`](docs/api.md).

## Architecture Decisions

- Domain-first package organization with thin entrypoints and shared runtime composition (`app/shared/http`).
- Settings use pydantic-settings with merge compatibility for nested legacy env structures.
- Talent Partner/candidate authorization is dependency-based; admin endpoints use explicit API key dependency.
- GitHub integration keeps transport/client/actions/artifact parsing concerns separated for testability.
- Durable job status uses polling endpoints plus worker handlers for async side effects.
- Worker health is tracked through a persisted heartbeat row per worker instance, which later readiness checks can inspect.

## Runtime Commands

- `./runBackend.sh` or `./runBackend.sh up`: start the API server and Winoe worker with local supervision.
- `./runBackend.sh api`: start the API server only.
- `./runBackend.sh worker`: start the Winoe worker only.
- `./runBackend.sh migrate`: load environment values and run Alembic migrations.
- `./runBackend.sh bootstrap-local`: seed the local demo Talent Partner accounts and repair missing company links.
- `./runBackend.sh retry-dead-jobs`: requeue dead-letter Winoe jobs after schema repair.
- `poetry run python scripts/local_demo_smoke_test.py`: verify readiness, create a Trial, and wait for scenario generation to reach a ready state.

## Tests and Verification

Run full test suite:

```bash
poetry run pytest
```

Docs verification/tooling commands:

```bash
poetry run python code-quality/documentation/scripts/docs_inventory.py --strict --markdown-output code-quality/documentation/latest/artifacts/docs_inventory.md
poetry run python code-quality/documentation/scripts/docs_env_inventory.py --strict --markdown-output code-quality/documentation/latest/artifacts/env_inventory.md
poetry run python code-quality/documentation/scripts/docs_api_export.py --strict --verify-doc README.md docs/api.md
poetry run python code-quality/documentation/scripts/docs_docstring_audit.py --include-module-docs --strict --json > code-quality/documentation/latest/artifacts/docstring_audit.json
git status --porcelain -- docs/api.md code-quality/documentation/latest/artifacts/openapi_snapshot.json code-quality/documentation/latest/artifacts/api_endpoint_matrix.md code-quality/documentation/latest/artifacts/api_endpoint_matrix.json code-quality/documentation/latest/artifacts/docs_inventory.md code-quality/documentation/latest/artifacts/env_inventory.md code-quality/documentation/latest/artifacts/docstring_audit.json
```

The `git status --porcelain` command should output nothing when generated docs are current.

## Deployment Notes

- Use PostgreSQL for runtime and migrations.
- Set strict CORS and CSRF origins in non-local environments.
- Keep `DEV_AUTH_BYPASS` disabled outside local development.
- Configure GitHub token/workflow/webhook secret for GitHub-native features.
- Configure real email provider credentials before enabling invite/schedule notifications.
- Rotate and protect all Auth0/GitHub/email/admin secrets; do not commit real values.
