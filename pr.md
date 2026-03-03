# P0 Infra: Durable Jobs + Worker Runner + Job Status API (Issue #194)

## TL;DR

- Added a durable DB-backed `jobs` model and migration with required fields, scheduling metadata, locking metadata, tenancy links, and correlation support.
- Added idempotent enqueue semantics via `create_or_get_idempotent` and a unique constraint on `(company_id, job_type, idempotency_key)`.
- Added a lightweight worker runner (`python -m app.jobs.worker`) with optimistic claim, lease-based stale reclaim, exponential backoff retries, and dead-letter transitions.
- Added authenticated polling API `GET /api/jobs/{job_id}` with stable response shape and `pollAfterMs` guidance.
- This enables restart-tolerant long-running workflows without coupling execution to request lifetimes.

## What changed

### DB schema

- Added `jobs` table in `alembic/versions/202603030001_add_durable_jobs_table.py`.
- Required columns shipped:
  - `job_type`
  - `status`
  - `attempt`
  - `max_attempts`
  - `idempotency_key`
  - `payload_json`
  - `result_json`
  - `last_error`
  - `created_at`
  - `updated_at`
  - `next_run_at`
- Additional operational columns:
  - `locked_at`
  - `locked_by`
  - `company_id`
  - `candidate_session_id`
  - `correlation_id`
- Added indexes for runnable selection and ownership lookup:
  - `ix_jobs_status_next_run_created`
  - `ix_jobs_company_id`
  - `ix_jobs_candidate_session_id`
  - unique `uq_jobs_company_job_type_idempotency_key`

### Idempotency

- Implemented `create_or_get_idempotent(...)` in `app/repositories/jobs/repository.py`.
- Behavior:
  - validates `job_type`, `idempotency_key`, `max_attempts`
  - validates payload size against `MAX_JOB_PAYLOAD_BYTES` before insert
  - checks existing row first
  - on race/`IntegrityError`, rolls back and fetches the existing row
- Uniqueness boundary is company-scoped: `(company_id, job_type, idempotency_key)`.

### Worker runner

- Added worker entrypoint: `python -m app.jobs.worker`.
- `run_once()` flow:
  - claims one runnable job using optimistic update on `(id, attempt)` + runnable predicate
  - sets `status=running`, increments `attempt`, writes `locked_at/locked_by`
  - dispatches to registered handler for `job_type`
- Runnable/claim behavior:
  - FIFO-ish order: `coalesce(next_run_at, created_at)`, then `created_at`
  - stale running jobs are reclaimed when lease expires (`locked_at <= now - lease_seconds`)
- Retry/dead-letter behavior:
  - transient exception: reschedule to `queued` with exponential backoff (`1s, 2s, 4s...` capped at `60s`)
  - when attempts exhausted: mark `dead_letter`
  - missing handler or permanent handler error: immediate `dead_letter`
- Logs include transition-safe metadata (`jobId`, `attempt`, `correlation_id`) and avoid payload logging.

### API: `GET /api/jobs/{job_id}`

- Added route in `app/api/routers/jobs.py`, mounted under `/api/jobs/{job_id}`.
- Response fields:
  - `jobId`
  - `jobType`
  - `status`
  - `attempt`
  - `maxAttempts`
  - `pollAfterMs`
  - `result`
  - `error`
- `pollAfterMs` rules:
  - `1500` for active states (`queued`, `running`)
  - `0` for terminal states
- Not found or not visible returns `404` with existing API error envelope (`detail`, `errorCode`, `retryable`, `details`) and `errorCode=JOB_NOT_FOUND`.

### Security and ownership

- No public create-job endpoint was introduced; job creation remains internal code path only.
- Recruiter reads are company-scoped (`job.company_id == recruiter.company_id`).
- Candidate reads require all of:
  - job tied to a `candidate_session_id` (company-scoped jobs with no candidate session are not candidate-readable)
  - `email_verified is True`
  - normalized invite-email match between token email and `candidate_sessions.invite_email`
  - sub mismatch protection: if `candidate_auth0_sub` is set and differs from principal `sub`, access is denied
- For not found and not owned cases, API intentionally returns `404`.
- Payload size validation is enforced before insert (`MAX_JOB_PAYLOAD_BYTES`).

### Error hygiene

- `last_error` is sanitized and bounded via repository helper:
  - whitespace/newline normalization to a single-line message
  - truncation to `MAX_JOB_ERROR_CHARS = 2048`

## Acceptance criteria mapping

1. Creating a job and restarting the API process does not lose it; worker can resume.
   - Satisfied by DB persistence (`jobs` table), decoupled worker process, and lease-based claim/reclaim logic.
2. Worker retries transient failures up to `max_attempts`, then marks dead-letter.
   - Satisfied by `run_once()` + `mark_failed_and_reschedule()` + `mark_dead_letter()` with attempt tracking and capped exponential backoff.
3. `GET /api/jobs/{id}` returns stable, documented JSON structure.
   - Satisfied by `JobStatusResponse` schema and route implementation returning fixed keys plus deterministic `pollAfterMs`.

## Testing

### Commands run and results

- `poetry run ruff check .` -> pass
- `poetry run ruff format .` -> pass (`731 files left unchanged`)
- `poetry run pytest -q` -> pass (`846 passed in 13.39s`)

### Key tests

- `tests/unit/test_jobs_repository.py::test_claim_next_runnable_prevents_double_claim_with_two_sessions`
- `tests/unit/test_jobs_repository.py::test_claim_next_runnable_never_reclaims_terminal_state_jobs`
- `tests/api/test_jobs_api.py::test_get_job_status_candidate_cannot_read_company_scoped_job`
- `tests/integration/test_jobs_worker_integration.py::test_worker_run_once_retry_then_success_with_new_sessions` (integration worker resume/retry path)
- `tests/unit/test_jobs_repository.py::test_mark_failed_and_reschedule_sanitizes_and_truncates_last_error`

### Manual QA

- Created jobs via internal repository APIs and exercised success, retry, and dead-letter paths with the worker runner.
- Verified ownership behavior on `GET /api/jobs/{job_id}` for authorized and unauthorized principals.
- Verified restart tolerance by stopping and restarting worker processing and confirming queued/stale jobs resumed.

## Demo / rollout checklist

1. Apply migration and start API as usual.
2. Create a job through an internal code path (example harness snippet below).
3. Start worker: `python -m app.jobs.worker`.
4. Poll status: `GET /api/jobs/{id}` and honor `pollAfterMs`.
5. Simulate restart: stop worker, start worker again, verify queued/stale-running work resumes.

```python
job = await jobs_repo.create_or_get_idempotent(
    db,
    job_type="scenario_generation",
    idempotency_key="demo-scenario-123",
    payload_json={"simulationId": simulation_id},
    company_id=company_id,
    candidate_session_id=candidate_session_id,
    correlation_id="req-demo-1",
)
print(job.id)
```

- Environment notes:
  - Migration is additive.
  - Docker Postgres is not required for the shape of this change in code/tests; SQLite-backed test suite passes.

## Risks / follow-ups

- Add optional worker `--once` flag for one-shot execution/cron style runs.
- Tune retry jitter/backoff policy per job type as load profile emerges.
- Expand handler registry with additional job types (scenario, transcript, evaluation) using same contract.
- Add richer observability (job duration histograms, queue depth metrics, dead-letter dashboards).
- Postgres runtime migration execution was not validated in this sandbox due to Docker restrictions; migration is additive and uses standard SQLAlchemy types/indexes.
