# Tenon Backend

FastAPI + Postgres backend for Tenon’s 5-day async simulations. Recruiters create simulations and invites; candidates authenticate via Auth0, work in GitHub (template repos + Codespaces + Actions), and recruiters review submissions with repo/workflow/commit/diff/test metadata.

## GitHub-Native Execution

- Template catalog source of truth: `app/services/tasks/template_catalog*.py` maps `templateKey` → template repo (`owner/name`) for day2/day3 code+debug tasks.
- Workflow expectations: `TENON_GITHUB_ACTIONS_WORKFLOW_FILE` must exist and support `workflow_dispatch`. Artifact contract: preferred artifact `tenon-test-results` (case-insensitive) containing `tenon-test-results.json` with `{passed, failed, total, stdout, stderr, summary?}`; fallback to any JSON with those keys, else JUnit XML.
- Flow: backend provisions a workspace repo from the template → returns Codespaces deep link → triggers/polls Actions runs → parses artifacts → stores run/test/diff metadata on `Workspace` and `Submission`. Diff summary uses GitHub compare from `base_template_sha` → run head SHA. Last run/test summary cached on `Workspace`.

## Architecture & Folders

- API app factory: `app/main.py`, `app/api/app_builder.py`; routers in `app/api/routers/*`; middleware in `app/api/middleware*.py`; error handlers in `app/api/errors/*`.
- Core: settings/env `app/core/settings/*`, DB `app/core/db`, auth/JWT/rate limits `app/core/auth/*`, proxy/request-size/perf/logging middleware `app/core/proxy_headers.py`, `app/core/request_limits.py`, `app/core/perf/*`, `app/core/logging/*`.
- Domains/Services: simulations/tasks `app/services/simulations/*`, `app/services/tasks/*`; candidate sessions `app/services/candidate_sessions/*`; submissions/workspaces/actions/diff `app/services/submissions/*`; presenters for recruiter views `app/domains/submissions/presenter/*`; notifications/email `app/services/notifications/*`.
- GitHub integration: REST client `app/integrations/github/client/*`; Actions runner + artifact parsing `app/integrations/github/actions_runner/*`, `app/integrations/github/artifacts/*`; template health checks `app/integrations/github/template_health/*`.
- Data models: SQLAlchemy models under `app/repositories/*` for `Simulation`, `Task`, `CandidateSession`, `Workspace`, `Submission`, `FitProfile`, `User`, `Company`; migrations in `alembic/versions`.

## Domain Glossary

- Simulation: recruiter-owned scenario with role/techStack/focus/templateKey.
- Task: daily assignment; types drive validation (`design`, `code`, `debug`, `handoff`, `documentation`); code/debug tasks carry template_repo.
- Candidate Session: invite with token, status, expiry, invite email, Auth0 bindings, invite email delivery metadata.
- Workspace: GitHub repo generated per candidate+task; stores default branch, base_template_sha, last run/test summary, codespace URL.
- Submission: final turn-in per task with contentText, repo path, commit/workflow ids, test counts/output, diff_summary_json, last_run_at.
- FitProfile: placeholder model for future AI evaluation output (not generated today).

## API Overview

- Auth/Health: `GET /health`; `GET /api/auth/me`; `POST /api/auth/logout`.
- Recruiter (recruiter:access): `GET/POST /api/simulations`; `GET /api/simulations/{id}`; `GET /api/simulations/{id}/candidates`; `POST /api/simulations/{id}/invite`; `POST /api/simulations/{id}/candidates/{csId}/invite/resend`; `GET /api/submissions`; `GET /api/submissions/{id}`.
- Candidate (candidate:access + invite token): `GET /api/candidate/session/{token}` and `POST /claim`; `GET /api/candidate/session/{id}/current_task`; `GET /api/candidate/invites`.
- GitHub-native tasks (candidate:access + `x-candidate-session-id`): `POST /api/tasks/{taskId}/codespace/init`; `GET /api/tasks/{taskId}/codespace/status`; `POST /api/tasks/{taskId}/run`; `GET /api/tasks/{taskId}/run/{runId}`; `POST /api/tasks/{taskId}/submit`.
- Admin (X-Admin-Key): `GET /api/admin/templates/health?mode=static`; `POST /api/admin/templates/health/run`.

## Typical Flow

1) Recruiter authenticates → `POST /api/simulations` (seeds tasks) → `POST /api/simulations/{id}/invite` to generate token + pre-provision workspaces and send email.  
2) Candidate opens invite with Auth0 login → claim via `/api/candidate/session/{token}` → fetch current task → for code/debug tasks call `/codespace/init`, work in Codespaces, `/run` to test, `/submit` to turn in.  
3) Recruiter reviews via `/api/submissions` list and `/api/submissions/{id}` detail (repo/workflow/commit/diff/test results).

## Configuration

- Database: `TENON_DATABASE_URL`, `TENON_DATABASE_URL_SYNC` (SQLite fallback for local if unset).
- Auth0: `TENON_AUTH0_DOMAIN` or `TENON_AUTH0_ISSUER`, `TENON_AUTH0_JWKS_URL`, `TENON_AUTH0_API_AUDIENCE`, `TENON_AUTH0_ALGORITHMS`, claim namespace/claim keys, leeway/cache TTL. App fails fast on missing issuer/audience outside tests. Dev bypass: `DEV_AUTH_BYPASS=1` allowed only with `ENV=local`.
- GitHub: `TENON_GITHUB_API_BASE`, `TENON_GITHUB_ORG`, `TENON_GITHUB_TEMPLATE_OWNER`, `TENON_GITHUB_REPO_PREFIX`, `TENON_GITHUB_ACTIONS_WORKFLOW_FILE`, `TENON_GITHUB_TOKEN`, `TENON_GITHUB_CLEANUP_ENABLED` (placeholder).
- App: `TENON_ENV`, `TENON_API_PREFIX`, `TENON_CANDIDATE_PORTAL_BASE_URL`, `TENON_MAX_REQUEST_BODY_BYTES`, `TENON_RATE_LIMIT_ENABLED`, `TENON_TRUSTED_PROXY_CIDRS`, `DEBUG_PERF`.
- Email: `TENON_EMAIL_PROVIDER` (console/resend/sendgrid/smtp), `TENON_EMAIL_FROM`, provider keys (`TENON_RESEND_API_KEY`, `SENDGRID_API_KEY`, `SMTP_*`).
- Admin: `TENON_ADMIN_API_KEY`. Security: redact tokens in logs; never log GitHub/Auth0 secrets; rotate if leaked. Rate limiter is in-memory per process—use shared store before multi-instance deploys.

## Local Development

- Install: `poetry install`; optionally `source ./setEnvVar.sh` to load defaults.
- Run: `poetry run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000` or `./runBackend.sh`.
- Migrations: `poetry run alembic upgrade head`.
- Seed dev recruiters: `ENV=local DEV_AUTH_BYPASS=1 poetry run python scripts/seed_local_recruiters.py`.
- Tests: `poetry run pytest` (see `tests/README.md`).
- Dev auth: recruiter bearer `recruiter:email@example.com` or `x-dev-user-email` when `DEV_AUTH_BYPASS=1`; candidate routes expect Auth0-style candidate bearer plus `x-candidate-session-id`.

## Roadmap (planned/not shipped)

- AI scenario/rubric generation and FitProfile reports.
- Background jobs, webhook ingestion/GitHub App auth, repo cleanup.
- Day4 media upload + transcription; Day5 structured documentation intake.
- Structured logging/monitoring/analytics/admin metrics; production deploy hardening (disable dev bypass).
