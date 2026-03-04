# P0 Recruiter Core: Persist simulation recruiter context + AI toggles (Issue #196)

## TL;DR

- Extended `POST /api/simulations` so recruiter context inputs are first-class API fields: `seniority`, `focus`, `companyContext`, and `ai` controls.
- Persisted new simulation context columns (`company_context`, `ai_notice_version`, `ai_notice_text`, `ai_eval_enabled_by_day`) and continued persisting role/focus in existing `seniority`/`focus` columns.
- Extended `GET /api/simulations/{id}` and `GET /api/simulations` responses to return these fields (list includes `seniority` and `ai.evalEnabledByDay`, and now also returns `companyContext` + `ai` summary).
- Wired scenario generation job enqueue in create flow to use a structured recruiter-context payload builder, including normalized/allowlisted values.
- Kept create flow atomic with a single outer transaction and deterministic idempotent job enqueue.

## What changed (detailed)

### API contract

- `POST /api/simulations` now accepts and validates:
  - `seniority` (with aliases `roleLevel` / `role_level`)
  - `focus` (with aliases `focusNotes` / `focus_notes`)
  - `companyContext` object with allowlisted keys only: `domain`, `productArea`
  - `ai` object with:
    - `noticeVersion`
    - `noticeText`
    - `evalEnabledByDay`
- `GET /api/simulations/{id}` returns the same persisted context fields:
  - `seniority`, `focus`, `companyContext`, `ai`
- `GET /api/simulations` includes summary fields (minimum required + more):
  - `seniority`
  - `ai.evalEnabledByDay` (via `ai`)
  - also includes `companyContext` and `ai.noticeVersion/noticeText` when present

### DB changes

- Added new nullable columns on `simulations`:
  - `company_context` (`JSON`)
  - `ai_notice_version` (`String(100)`)
  - `ai_notice_text` (`Text`)
  - `ai_eval_enabled_by_day` (`JSON`)
- Migration file:
  - `alembic/versions/202603040001_add_simulation_context_columns.py`

### Scenario generation integration

- Added structured payload builder:
  - `app/services/simulations/scenario_payload_builder.py::build_scenario_generation_payload`
- Payload now includes `recruiterContext` with normalized fields:
  - `seniority`
  - `focus`
  - `companyContext`
  - `ai` (`noticeVersion`, `noticeText`, `evalEnabledByDay`)
- Create flow enqueues a `scenario_generation` durable job using this payload:
  - `app/services/simulations/creation.py::create_simulation_with_tasks`
- Idempotency key format:
  - `simulation:{simulation_id}:scenario_generation`
- Why this idempotency key is safe:
  - Jobs are deduplicated by `(company_id, job_type, idempotency_key)` unique constraint, so retries/races for the same simulation resolve to one logical queued job per company.

### Transactionality / invariants

- `create_simulation_with_tasks` uses one outer transaction for:
  - simulation insert
  - task seeding
  - status transition to `ready_for_review`
  - scenario job enqueue
- Explicit `flush` happens before payload/idempotency-key construction so `sim.id` is materialized before:
  - building job payload (`simulationId`)
  - constructing idempotency key (`simulation:{id}:scenario_generation`)
- Job enqueue uses `commit=False` so the job insert participates in the same outer transaction and commits atomically with simulation creation.

## Validation + security notes

- `companyContext` validation is strict/allowlisted:
  - only `domain` and `productArea`
  - unknown keys rejected (`extra="forbid"`)
- `ai.evalEnabledByDay` is strict:
  - day keys must be `"1"`..`"5"` only
  - values must be booleans (`StrictBool`)
- Size limits are enforced via constants in `app/schemas/simulations.py`:
  - `MAX_FOCUS_NOTES_CHARS = 1000`
  - `MAX_COMPANY_CONTEXT_VALUE_CHARS = 120`
  - `MAX_AI_NOTICE_VERSION_CHARS = 100`
  - `MAX_AI_NOTICE_TEXT_CHARS = 2000`
- Logging posture:
  - no new logs were added in create/payload paths that emit raw `focus` or AI notice text
  - full focus/notice contents are not logged by this change set

## Testing

Commands run (all passed):

- `poetry run ruff check .`
- `poetry run ruff format --check .`
- `poetry run pytest`

Key AC1-AC4 coverage (from Worker Report):

- AC1 (create returns persisted fields):
  - `tests/api/test_simulations_detail.py::test_simulation_context_round_trips_on_create_and_detail`
- AC2 (detail returns same persisted fields):
  - `tests/api/test_simulations_detail.py::test_simulation_context_round_trips_on_create_and_detail`
- AC3 (list includes summary fields):
  - `tests/api/test_simulations_list.py::test_list_simulations_includes_seniority_and_ai_eval_summary`
- AC4 (scenario job payload consumes fields):
  - `tests/unit/test_simulations_service.py::test_create_simulation_with_tasks_enqueues_scenario_generation_job`
  - plus payload-builder unit coverage:
    - `tests/unit/test_scenario_payload_builder.py::test_build_scenario_generation_payload_includes_recruiter_context_fields`

## Risks / rollout

- Risk level: low.
  - Migration is additive and uses nullable columns, so it is backward-compatible for existing rows.
- Transaction control note:
  - Jobs repository supports `commit=False` for outer transaction control, which this create flow uses.

Demo checklist:

1. Create a simulation with `seniority`, `focus`, `companyContext`, and `ai.evalEnabledByDay`.
2. Fetch simulation detail and verify fields round-trip unchanged.
3. List simulations and verify `seniority` + `ai.evalEnabledByDay` summary presence.
4. Confirm enqueued `scenario_generation` job payload contains `recruiterContext` fields.
