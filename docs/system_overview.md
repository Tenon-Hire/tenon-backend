# Tenon Backend System Overview

This document summarizes implemented, partial, and planned behavior for the Tenon backend codebase as of this snapshot.

## Architecture Summary
- **App entrypoint**: `app/main.py` → `app/api/app_builder.py` builds FastAPI app with middleware (CORS, proxy headers, request size limits, optional perf logging) and registers routers via `app/api/router_registry.py`. Startup runs `init_db_if_needed` for SQLite fallback (`app/api/lifespan.py`).
- **Core**: settings/env (`app/core/settings/*`), DB (`app/core/db` async SQLAlchemy with SQLite fallback), auth/JWT/rate limits (`app/core/auth/*`), logging/redaction (`app/core/logging/*`), perf (`app/core/perf/*`), proxy/request limits (`app/core/proxy_headers.py`, `app/core/request_limits.py`).
- **Domains/Services** (business logic lives in `app/services/*`, re-exported under `app/domains/*`):
  - Simulations & tasks (`app/services/simulations/*`, `app/services/tasks/*`): create/list simulations, seed 5-day tasks, resolve templateKey→template repo.
  - Candidate sessions (`app/services/candidate_sessions/*`): invite token issuance/claim, ownership enforcement, progress snapshot, invite listings.
  - Submissions & GitHub-native execution (`app/services/submissions/*`): workspace provisioning, Codespaces URLs, Actions dispatch/polling, artifact parsing, diff summaries, submission persistence, recruiter presenters.
  - Notifications/email (`app/services/notifications/*`, providers in `app/integrations/notifications/email_provider/*`).
- **GitHub integration**: REST client (`app/integrations/github/client/*`), Actions runner (`app/integrations/github/actions_runner/*`) with workflow fallbacks/caching/artifact parsing (`app/integrations/github/artifacts/*`), workspaces repo/model (`app/repositories/github_native/workspaces/*`), template health checks (`app/integrations/github/template_health/*`).
- **Data models**: SQLAlchemy models for `Simulation`, `Task`, `CandidateSession`, `Workspace`, `Submission`, `FitProfile`, `User`, `Company` in `app/repositories/*`; migrations in `alembic/versions`.

## Subsystem Documentation
### Auth
- **Purpose**: Authenticate recruiters and candidates via Auth0 access tokens; enforce permission strings `recruiter:access` / `candidate:access`. Dev bypass for local/test via bearer token `recruiter:email`/`candidate:email` or header `x-dev-user-email` when `DEV_AUTH_BYPASS=1`.
- **Code**: `app/core/auth/*` (JWT decode, principal building, role checks, rate limits), `app/api/routers/auth.py`.
- **Models**: `User` (auto-created for recruiters on first login). No candidate user record required; candidate identity stored on `CandidateSession`.
- **Interactions**: Candidate endpoints depend on `require_candidate_principal`; recruiter endpoints on `get_current_user` + role guard. Rate limits on `/api/auth/me`. Dev bypass blocked outside ENV=local.
- **Partial**: No audit/metrics; email verification relies on Auth0 `email_verified` claim only.

### Simulations & Tasks
- **Purpose**: 5-day blueprint seeding design/code/debug/handoff/documentation tasks per simulation; templateKey drives code/debug template repo.
- **Code**: `app/services/simulations/creation.py`, `task_seed.py`, `task_templates.py`, `template_keys.py`; template catalog `app/services/tasks/template_catalog*.py`; routers `app/api/routers/simulations_routes/*`.
- **Models**: `Simulation`, `Task`.
- **Interactions**: Recruiter creates simulation (validates templateKey) → seeds tasks with template_repo for day 2/3 code/debug. Ownership enforced on reads/list. Focus stored as text.
- **Planned/roadmap**: AI scenario/rubric generation; broader pre-provisioning lifecycle hooks.

### Candidate Sessions & Progression
- **Purpose**: Invite tokens, claim flows, progress tracking through tasks, invite list for candidates.
- **Code**: `app/services/candidate_sessions/*`, repositories under `app/repositories/candidate_sessions/*`, schemas `app/schemas/candidate_sessions.py`; routers `app/api/routers/candidate_sessions_routes/*`.
- **Models**: `CandidateSession` (status, expires_at, invite email delivery fields).
- **Interactions**: Invite token TTL 14d; claim requires Auth0 email_verified + email match; status set to in_progress on claim; current task endpoint auto-completes simulation when done; invite list aggregates progress/last activity; rate limits on claim/current_task/invites.
- **Partial**: Expiry enforced on claim only; invite resend does not retry beyond status fields.

### Submissions (including run/test/diff persistence)
- **Purpose**: Enforce task order/duplicates, store submissions with test/diff metadata, expose recruiter views.
- **Code**: `app/services/submissions/*`, presenters `app/domains/submissions/presenter/*`, schemas `app/schemas/submissions.py`; routers `app/api/routers/submissions_routes/*`.
- **Models**: `Submission`, `FitProfile` (placeholder, not generated).
- **Interactions**: Validates branch names and payloads; computes progress on submit; recruiter list/detail include repo/commit/workflow/diff/test results with truncation/redaction; diff summaries from GitHub compare; test outputs parsed from JSON/JUnit artifacts.

### GitHub-Native Execution
- **Purpose**: Provision workspace repos from templates, deliver Codespaces links, dispatch/poll Actions workflows, parse artifacts, cache run/test state.
- **Code**: Workspace provisioning `workspace_provision.py`, `workspace_template_repo.py`, `workspace_existing.py`; Codespaces URLs `codespace_urls.py`; Actions dispatch/poll `run_service.py`, `use_cases/run_tests.py`, `fetch_run.py`; artifact parsing `app/integrations/github/actions_runner/*` + `app/integrations/github/artifacts/*`; diff summaries `use_cases/submit_diff.py`; persistence `app/repositories/github_native/workspaces/*`.
- **Artifact contract**: Preferred artifact names include `tenon-test-results`; expect JSON `{passed, failed, total, stdout, stderr, summary?}`, fallback to any JSON with those keys then JUnit XML.
- **Rate limits/throttles**: Per-session limits on init/run/poll/submit; poll min interval; concurrency guards.
- **Partial**: GitHub cleanup flag exists but no deletion; no GitHub App auth/webhooks yet.

### Recruiter Visibility
- **Purpose**: Recruiter dashboards for simulations, candidates, and submissions with GitHub links.
- **Code**: `app/api/routers/simulations_routes/*`, `app/api/routers/submissions_routes/*`, presenters `app/domains/submissions/presenter/*`.
- **Interactions**: Ownership enforced via recruiter id; submissions list/detail provide repo/workflow/commit/diff URLs and parsed test results; fit_profile presence surfaced as `hasFitProfile` only.

### Analytics/Logging/Monitoring
- **Current**: Optional perf logs (DB counts/timing) when `DEBUG_PERF` set; log redaction of tokens; rate limiter is in-memory per-process.
- **Planned**: Structured logging/monitoring/admin metrics; shared rate-limit store for multi-instance deploys.

### AI Gen/Eval/Reports
- **Current**: FitProfile model/migrations only; no generation or usage.
- **Planned**: AI scenario/rubric generation, AI repo tailoring commits, FitProfile report generation.

## API Reference (high-level)
### Recruiter (recruiter:access)
- `GET /api/simulations` list owned (with candidate counts).
- `POST /api/simulations` create simulation, seed 5 tasks (templateKey required).
- `GET /api/simulations/{id}` detail with tasks.
- `GET /api/simulations/{id}/candidates` list candidate sessions with invite email status and `hasFitProfile`.
- `POST /api/simulations/{id}/invite` create/resend invite, pre-provision workspaces, send email (rate-limited; 409 if candidate already completed).
- `POST /api/simulations/{id}/candidates/{csId}/invite/resend` resend invite email.
- `GET /api/submissions` list submissions (filters: candidateSessionId, taskId) with repo/commit/workflow/diff/test summaries.
- `GET /api/submissions/{id}` submission detail with contentText, repo info, test results, diff summary, links.

### Candidate (candidate:access, invite token)
- `GET /api/candidate/session/{token}` claim/init invite; 404 invalid, 410 expired, 403 email mismatch/unverified.
- `POST /api/candidate/session/{token}/claim` idempotent claim.
- `GET /api/candidate/session/{id}/current_task` (requires `x-candidate-session-id` header) returns current task/progress, auto-completes when finished.
- `GET /api/candidate/invites` list invites for Auth0 email with progress/expiry/token.

### GitHub-Native Tasks (candidate:access + `x-candidate-session-id`)
- `POST /api/tasks/{taskId}/codespace/init` create/return workspace repo + Codespaces link; payload `githubUsername`.
- `GET /api/tasks/{taskId}/codespace/status` workspace metadata + last run summary.
- `POST /api/tasks/{taskId}/run` trigger Actions workflow (code/debug only); returns normalized run status/pollAfterMs.
- `GET /api/tasks/{taskId}/run/{runId}` fetch/poll existing run (throttled).
- `POST /api/tasks/{taskId}/submit` enforce order/duplication; for code/debug runs tests, stores commit/workflow ids and diff summary; returns progress/isComplete.

### Auth/Health
- `GET /health` liveness (no auth).
- `GET /api/auth/me` returns current recruiter user; rate-limited.
- `POST /api/auth/logout` stateless 204.

### Admin (X-Admin-Key)
- `GET /api/admin/templates/health?mode=static` static template validation.
- `POST /api/admin/templates/health/run` live workflow dispatch/validation (templateKeys, timeoutSeconds, concurrency ≤5).

## Environment & Configuration
- Core: `TENON_ENV`, `TENON_API_PREFIX`, `TENON_MAX_REQUEST_BODY_BYTES`, `TENON_RATE_LIMIT_ENABLED`, `TENON_TRUSTED_PROXY_CIDRS`, `DEBUG_PERF`.
- Database: `TENON_DATABASE_URL`, `TENON_DATABASE_URL_SYNC` (SQLite fallback local).
- Auth0: `TENON_AUTH0_DOMAIN`/`TENON_AUTH0_ISSUER`, `TENON_AUTH0_JWKS_URL`, `TENON_AUTH0_API_AUDIENCE`, `TENON_AUTH0_ALGORITHMS`, `TENON_AUTH0_CLAIM_NAMESPACE`, email/roles/permissions claim keys, `TENON_AUTH0_LEEWAY_SECONDS`, `TENON_AUTH0_JWKS_CACHE_TTL_SECONDS`. Dev bypass: `DEV_AUTH_BYPASS=1` (local only; app refuses non-local).
- GitHub: `TENON_GITHUB_API_BASE`, `TENON_GITHUB_ORG`, `TENON_GITHUB_TEMPLATE_OWNER`, `TENON_GITHUB_REPO_PREFIX`, `TENON_GITHUB_ACTIONS_WORKFLOW_FILE`, `TENON_GITHUB_TOKEN`, `TENON_GITHUB_CLEANUP_ENABLED` (not used).
- App: `TENON_CANDIDATE_PORTAL_BASE_URL`.
- Email: `TENON_EMAIL_PROVIDER`, `TENON_EMAIL_FROM`, provider keys (`TENON_RESEND_API_KEY`, `SENDGRID_API_KEY`, `SMTP_*`).
- Admin: `TENON_ADMIN_API_KEY`.
- Security notes: never log tokens; Actions workflow inputs should avoid secrets; rotate GitHub/Auth0/email creds if leaked; rate limiter is in-memory per process.

## Local Development
- Install: `poetry install`; optional `source ./setEnvVar.sh` to load defaults (do not commit secrets).
- Run: `poetry run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000` or `./runBackend.sh` (seeds dev recruiters with `DEV_AUTH_BYPASS=1`).
- Migrations: `poetry run alembic upgrade head`.
- Seed dev recruiters: `ENV=local DEV_AUTH_BYPASS=1 poetry run python scripts/seed_local_recruiters.py`.
- Tests: `poetry run pytest` (see `tests/README.md` for layout).
- Dev auth: recruiter bearer `recruiter:email@example.com` or header `x-dev-user-email` when dev bypass enabled; candidate routes still expect Auth0-style bearer + `x-candidate-session-id`.

## Planned / Not Yet Implemented
- AI scenario/rubric generation, AI repo tailoring commits, FitProfile report generation.
- Background jobs system; webhook ingestion + GitHub App auth migration; repository cleanup after evaluations.
- Day4 media upload/transcription pipeline; Day5 structured documentation intake.
- Structured logging/monitoring/admin metrics; production hardening (shared rate limits, disable dev bypass).
