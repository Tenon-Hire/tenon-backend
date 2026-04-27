# PR: Add operator endpoints for failed jobs and retry controls

## Summary

- Adds admin-only operator visibility for failed background jobs so production and demo operators can inspect failures without reading worker logs or raw job payloads.
- Adds retry controls for dead-letter jobs, including safe state transition back to `queued`.
- Surfaces safe, human-readable failure summaries on Trial detail through `backgroundFailures`.
- Extends local/dev admin QA support with real DB-backed admin users while preserving production JWT/Auth0 admin role behavior.
- Covers auth, retry behavior, redaction, Trial scoping, and route/detail regressions with focused and full-suite tests.

## What Changed

- Added `GET /api/admin/jobs/failed` to list failed and dead-letter background jobs for admins.
- Added `POST /api/admin/jobs/{job_id}/retry` to retry retryable dead-letter jobs.
- Added safe failure reason summaries that avoid exposing secrets, stack traces, bearer tokens, API keys, GitHub tokens, or raw payloads.
- Added Trial detail `backgroundFailures` so failed generation/evaluation work is visible in the Trial view.
- Scoped Trial failure visibility to the relevant Trial and company.
- Supported local/dev admin auth via `x-dev-user-email` only when the email belongs to a real DB user with `role="admin"`.
- Kept production admin auth on the existing JWT/Auth0 admin role path.
- Removed generated `issue-305-iteration*.diff` artifacts from the PR contents.

## API Changes
### `GET /api/admin/jobs/failed`

- Returns a failed-job listing for admin operators.
- Includes safe job metadata and human-readable failure reason summaries.
- Restricts access to admin users only.
- Rejects unauthenticated requests with `401`.
- Rejects Talent Partner and candidate access with `403`.

### `POST /api/admin/jobs/{job_id}/retry`

- Retries a dead-letter job by moving it back to `queued`.
- Returns `404 JOB_NOT_FOUND` for unknown job IDs.
- Returns `409 JOB_NOT_RETRYABLE` when the job is not in a retryable dead-letter state.
- Restricts access to admin users only.

### Trial detail `backgroundFailures`

- Adds `backgroundFailures` to Trial detail responses.
- Reports safe failure summaries for failed background jobs tied to the Trial.
- Excludes unrelated Trial failures.
- Preserves company scoping; cross-company Trial access returns `404`.

## Security / Access Control

- Operator endpoints are admin-only.
- Local/dev admin QA uses `x-dev-user-email` with a real DB user whose `role="admin"`.
- Production auth still relies on the existing JWT/Auth0 admin role path.
- Talent Partner and candidate access to operator endpoints returns `403`.
- Unauthenticated access to operator endpoints returns `401`.
- Cross-company Trial access remains hidden with `404`.

## Failure Reason Redaction

- Failure summaries are human-readable but safe for operator UI/API use.
- Raw secrets, stack traces, bearer tokens, API keys, GitHub tokens, and raw payloads are not exposed.
- Redaction behavior is covered by focused tests and manual API QA.

## Data / Migration Notes

- No migration was needed because existing job fields were sufficient.
- `failedAt` uses `updated_at` for dead-letter rows because the job model has no dedicated `failed_at`.
- Retry reuses existing job state fields and moves retryable dead-letter jobs back to `queued`.
- Generated `issue-305-iteration*.diff` artifacts were removed/not included.

## QA Evidence
### Automated

- Ruff: poetry run ruff check app tests — passed
- Focused #305 tests: 17 passed
- Route pattern regression: 1 passed
- Trial detail snapshot regression: 1 passed
- Full suite: 1850 passed, 13 warnings
- Coverage: 96.06%

### Manual API QA

- Admin failed-job list returned `200`
- Talent Partner and candidate access returned `403`
- Unauthenticated access returned `401`
- Retry dead-letter job returned `200`
- Retried job moved to `queued`
- Unknown job returned `404 JOB_NOT_FOUND`
- Non-retryable job returned `409 JOB_NOT_RETRYABLE`
- Trial detail returned `backgroundFailures`
- Unrelated Trial failures excluded
- Cross-company Trial access returned `404`
- Raw secrets, stack traces, bearer tokens, API keys, GitHub tokens, and raw payloads were not exposed

### Grep Verification

- Changed-file legacy terminology grep: no hits
- Changed-file retired v3 terminology grep: no hits

## Risks / Follow-ups

- `failedAt` is derived from `updated_at` for dead-letter rows until the job model grows a dedicated failure timestamp.
- Retry behavior is intentionally limited to retryable dead-letter jobs; broader operator workflows can build on these endpoints later.

Fixes #305
