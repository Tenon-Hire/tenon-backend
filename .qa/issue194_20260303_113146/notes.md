# Issue #194 Manual QA Notes

## Scope validated

- Migration inspection confirmed required durable-job columns and required indexes/unique constraint.
- Scratch DB migration flow validated with SQLite fallback:
  - full `alembic upgrade head` attempted and documented failure on historical SQLite-incompatible constraint migration.
  - fallback used: create baseline schema (excluding `jobs`) + `alembic stamp 202507200001` + `alembic upgrade 202603030001`.
- Internal job creation path validated via `jobs_repo.create_or_get_idempotent` (no public create endpoint).
- Worker behavior validated with `worker.run_once`:
  - success path
  - retry/backoff path (first fail then succeed)
  - dead-letter path after max attempts
  - resume after simulated worker restart with a new worker id
- API ownership/status validated in app context via FastAPI AsyncClient harness:
  - owner recruiter -> 200
  - wrong recruiter -> 404 (`JOB_NOT_FOUND`, `retryable=false`)
  - owning candidate on candidate-scoped job -> 200
  - non-owning candidate -> 404
  - candidate on company-scoped job -> 404
  - queued response includes `pollAfterMs=1500`

## Caveats

- Postgres server is unavailable in this sandbox, so manual QA used SQLite fallback path documented above.
- Git index writes are blocked in this sandbox (`.git/index.lock: Operation not permitted`), so `pr.md` could not be staged here.
