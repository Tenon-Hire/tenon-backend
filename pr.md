# Issue #221: CSRF/CORS hardening for BFF routes with Origin/Referer enforcement

## TL;DR
- Origin/Referer enforcement is now applied to cookie-bearing state-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) on protected API prefixes.
- CORS posture is now strict outside `local/test`: explicit allowlist required, wildcard and regex loosening rejected.
- CSRF violations return explicit `CSRF_ORIGIN_MISMATCH` payloads.
- Mixed cookie+bearer requests no longer bypass cookie CSRF checks.
- Default CSRF protected scope now follows `TENON_API_PREFIX` (typically `/api`).
- Manual runtime QA passed on real localhost + fresh Postgres.

## Problem / Why
- Cookie-based browser/BFF traffic needs CSRF protection for state-changing requests.
- Non-local CORS must reject wildcard/regex looseness and require explicit origins.
- Default CSRF scope must point at real backend API routes, not inert `/api/backend`.

## What changed
- `app/api/middleware_http.py`
  - CSRF middleware enforcement for `POST/PUT/PATCH/DELETE`.
  - `Origin` validation with `Referer` fallback when `Origin` is missing.
  - Enforcement scoped to cookie-bearing requests on protected path prefixes.
  - Mixed cookie+bearer no longer bypasses CSRF.
  - Default protected scope derived from `TENON_API_PREFIX`.
- `app/core/settings/settings.py`
  - Non-local CORS posture validation (explicit origins required; wildcard and regex rejected outside `local/test`).
  - CSRF env parsing/default behavior for allowed origins and protected prefixes.
- Tests
  - Exact CSRF error contract assertions.
  - Real route coverage for CSRF/CORS behavior.
  - Logging hygiene checks for CSRF rejections.
- Docs/env example
  - Updated security notes and defaults for CSRF/CORS posture.

## Security posture / invariants
- Protected state-changing requests with cookies must present an allowed `Origin` or allowed `Referer` origin.
- Bearer-only requests without cookies are not subject to cookie CSRF checks.
- Mixed cookie+bearer requests do not bypass CSRF.
- Wildcard CORS and CORS origin regex are rejected outside `local/test`.
- CSRF rejection logs exclude cookies and authorization headers.
- These invariants were verified by both automated tests and manual runtime QA.

## Configuration changes
- `TENON_CORS_ALLOW_ORIGINS`
- `TENON_CORS_ALLOW_ORIGIN_REGEX`
- `TENON_CSRF_ALLOWED_ORIGINS`
- `TENON_CSRF_PROTECTED_PATH_PREFIXES`
- Default protected scope follows `TENON_API_PREFIX` (typically `/api`).

## Testing
### Automated verification
- `poetry run pytest tests/unit/test_csrf_cors_hardening.py -q --no-cov` -> PASS
- `poetry run pytest -q` -> PASS
- `poetry run ruff check .` -> PASS
- `poetry run ruff format --check .` -> PASS

Key tests:
- `test_default_protected_prefix_covers_real_backend_route`
- `test_protected_post_with_disallowed_origin_returns_csrf_error`
- `test_protected_post_with_cookie_and_bearer_disallowed_origin_returns_csrf_error`
- `test_bearer_only_requests_bypass_cookie_csrf_enforcement`
- `test_csrf_rejection_logs_exclude_cookie_and_authorization`
- Non-local CORS validation tests:
  - `test_non_local_cors_rejects_wildcard_origins`
  - `test_non_local_cors_rejects_origin_regex`
  - `test_non_local_cors_requires_explicit_origins`

### Manual runtime QA
- Runtime method:
  - Real localhost FastAPI server via uvicorn on `127.0.0.1:8016`.
  - No ASGI fallback used.
- Fresh Postgres DB:
  - `tenon_issue221_manualqa_20260316_113447`
- Environment posture:
  - `TENON_ENV=staging`
  - Explicit allowlist: `["https://frontend.tenon.ai"]`
- Migrations:
  - `alembic upgrade head` succeeded.
  - Alembic version verified as `202603150002`.
- Evidence bundle:
  - `.qa/issue221/manual_qa_20260316_113447/`

Scenario outcomes:
- A: bad `Origin` + cookie -> `403` with exact payload `{"error":"CSRF_ORIGIN_MISMATCH","message":"Request origin not allowed."}`
- B: allowed `Origin` + cookie -> `204` (not CSRF-blocked)
- C: allowed `Referer` + cookie -> `204` (not CSRF-blocked)
- D1/D2: missing or bad `Referer` + cookie -> `403` with exact `CSRF_ORIGIN_MISMATCH` payload
- E: cookie + bearer + bad `Origin` -> `403` with exact `CSRF_ORIGIN_MISMATCH` payload
- F: bearer-only + bad `Origin` -> `204` (not CSRF-blocked)
- G: allowed preflight -> `200`, includes `access-control-allow-origin: https://frontend.tenon.ai`
- H: disallowed preflight -> `400 Bad Request`, body `Disallowed CORS origin`
- I: wildcard CORS in non-local env -> startup/config validation failure
- J: no sentinel cookie/bearer secret leakage in logs; CSRF rejection entries present

DB verification:
- `SELECT 1` passed.
- `current_database()` returned `tenon_issue221_manualqa_20260316_113447`.
- `SELECT version_num FROM alembic_version` returned `202603150002`.

## Risks / limitations
- Backend auth dependencies are currently bearer-based.
- CSRF protection here is aimed at cookie-bearing browser/BFF traffic hitting protected API routes.
- Future non-browser clients that send cookies to protected state-changing endpoints will need valid `Origin`/`Referer` or explicit path scoping.
- This PR does not implement CSRF tokens; it implements the MVP posture: Origin/Referer enforcement + strict CORS.
- QA note: localhost verification used a persistent PTY-hosted uvicorn process because non-persistent background processes were torn down in the sandbox environment.

## Rollout / demo checklist
- Configure explicit non-local allowlist origins.
- Demonstrate fake-origin POST returns exact `403` payload (`CSRF_ORIGIN_MISMATCH`).
- Demonstrate allowed `Origin`/`Referer` request succeeds.
- Demonstrate disallowed CORS preflight fails.
- Demonstrate bearer-only request still works.

## PR readiness verdict
- Ready for PR raise.
- Automated verification passed.
- Manual runtime QA passed with artifact-backed evidence.
