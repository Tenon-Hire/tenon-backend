# Title
Issue #206: Scenario generation job + recruiter status lifecycle (`generating` -> `ready_for_review`)

## TL;DR
- `POST /api/simulations` now creates simulations in `status="generating"` and returns `scenarioGenerationJobId`.
- A durable `scenario_generation` worker flow is wired through job enqueue + worker handler registration.
- Worker execution creates/reuses `ScenarioVersion v1`, persists generated storyline/tasks/rubric + generation metadata, and updates seeded task descriptions/scores.
- On successful generation, simulation status transitions to `ready_for_review` and active scenario version is set.
- Recruiter simulation detail now surfaces generated scenario content (`storylineMd`, `taskPromptsJson`, `rubricJson`) and metadata (`modelName`, `modelVersion`, `promptVersion`, `rubricVersion`).
- Deterministic template-catalog fallback is used when LLM keys are absent, demo mode is enabled, or LLM generation fails, and is stable for identical `(role, techStack, templateKey)` inputs.

## Problem / Why
Recruiters need a clear and trustworthy simulation lifecycle: create simulation, see `Generating...`, then review finalized scenario content before activation/invites. Without durable job tracking, the system cannot provide reliable async progress or failure visibility.

For MVP/demo reliability, deterministic fallback is required so scenario output remains reproducible even when LLM access is disabled, unavailable, or errors.

## What changed
### Simulation creation API
- `POST /api/simulations` now returns `scenarioGenerationJobId` in `SimulationCreateResponse`.
- New simulations are persisted with `status="generating"` (and `generating_at` set).
- Scenario generation is enqueued during create flow.

### Job / worker flow
- Added/wired `scenario_generation` in job handler exports and worker builtin handler registration.
- New handler: `app/jobs/handlers/scenario_generation.py`.
- Handler loads simulation + seeded tasks, generates scenario payload, and persists/updates `ScenarioVersion v1`.
- Generated storyline/task prompts/rubric are saved to scenario version; seeded task `description`, `title`, and rubric-weight-based `max_score` are updated.
- On success, simulation `active_scenario_version_id` is set and status is transitioned to `ready_for_review`.

### Public Jobs API contract
- Jobs API maps internal durable terminal states to public polling states:
- `succeeded` -> `completed`
- `dead_letter` -> `failed`
- `queued`/`running` remain unchanged for polling.

### Detail read-path
- Recruiter simulation detail now renders active scenario content and metadata from `ScenarioVersion`.
- Exposed scenario fields include:
- `storylineMd`
- `taskPromptsJson`
- `rubricJson`
- `modelName`, `modelVersion`, `promptVersion`, `rubricVersion`

### Deterministic fallback
- Scenario source selection uses deterministic fallback when:
- LLM credentials are absent, or
- demo mode is enabled, or
- LLM generation raises an error.
- Fallback generation is deterministic per `(role, techStack, templateKey)` via stable input hashing/template selection.

### Failure behavior
- If scenario generation fails to complete, the job transitions to failed (`dead_letter` internally, `failed` publicly).
- Simulation remains in `generating` and does not get an active scenario version.

### Idempotency / retries
- Enqueue layer idempotency key: `simulation:{id}:scenario_generation`.
- Handler layer reuses existing `ScenarioVersion v1` (version index `1`) under lock, avoiding duplicate `v1` rows on retries/replays.

## Acceptance criteria coverage
- Create simulation returns `status=generating` + `scenarioGenerationJobId`:
  - Covered by `tests/api/test_scenario_generation_flow.py::test_create_simulation_returns_generating_and_scenario_job_id`
  - Also covered in create-route tests (`tests/api/test_simulations_create.py`)
- Job creates `ScenarioVersion v1`:
  - Covered by `tests/api/test_scenario_generation_flow.py::test_scenario_generation_job_creates_v1_and_updates_detail_read`
  - Idempotent `v1` reuse verified by `tests/unit/test_scenario_generation_handler.py`
- Simulation transitions to `ready_for_review`:
  - Covered by scenario generation flow + handler tests.
- Simulation detail exposes generated scenario content:
  - Covered by detail assertions in scenario generation flow test (`storylineMd`, `taskPromptsJson`, `rubricJson`, metadata fields).
- Deterministic fallback is stable for identical inputs:
  - Covered by `tests/unit/test_scenario_generation_service.py::test_deterministic_template_generation_is_stable_for_same_inputs`.
- Failure path keeps simulation `generating` and exposes failed job:
  - Covered by API + handler failure tests in scenario generation flow/handler suites.

## Files changed
### API / schemas
- `app/api/routers/simulations_routes/create.py`
- `app/api/routers/simulations_routes/detail_render.py`
- `app/api/routers/jobs.py`
- `app/schemas/simulations.py`

### Simulation generation services / jobs
- `app/services/simulations/creation.py`
- `app/services/simulations/scenario_payload_builder.py`
- `app/services/simulations/scenario_generation.py`
- `app/jobs/handlers/scenario_generation.py`
- `app/jobs/handlers/__init__.py`
- `app/jobs/worker.py`

### Major test areas
- Jobs API status mapping (`tests/api/test_jobs_api.py`)
- End-to-end scenario generation flow (`tests/api/test_scenario_generation_flow.py`)
- Scenario generation service behavior/fallback (`tests/unit/test_scenario_generation_service.py`)
- Scenario generation handler behavior/idempotency/failure (`tests/unit/test_scenario_generation_handler.py`)
- Simulation lifecycle/create alignment and payload wiring (`tests/unit/test_simulations_service.py`, `tests/api/test_simulations_lifecycle.py`, `tests/api/test_simulations_create.py`)
- Detail read-path exposure and cross-flow regressions (API/integration suite updates)

## Testing
- `poetry run pytest --no-cov -q tests/api/test_jobs_api.py tests/api/test_scenario_generation_flow.py tests/unit/test_scenario_generation_service.py tests/unit/test_scenario_generation_handler.py tests/unit/test_simulations_service.py` -> PASS (`62 passed`)
- `./precommit.sh` -> PASS
- Full suite within precommit -> `1106 passed`
- Coverage output within precommit -> `Total coverage: 99.04%`
- Manual/runtime audit QA (`.qa/issue206/manual_qa_20260309T152525Z`, 2026-03-09) -> PASS (scenarios A-H)

Key validated areas:
- Jobs API state mapping and poll semantics.
- Scenario generation create/enqueue/run flow.
- Scenario handler/service fallback + metadata persistence.
- Simulation lifecycle alignment to `ready_for_review`.
- Detail read-path scenario payload exposure.
- Retry/idempotency behavior across enqueue and handler layers.
- Failure path preserves `generating` simulation state.

## Audit QA (manual / runtime)
- Overall verdict: `PASS`
- Runtime method summary:
  - Attempted localhost runtime first (`uvicorn` + `curl` probe).
  - Sandbox blocked bind on `127.0.0.1:8016` (`[Errno 1] operation not permitted`), so verification used ASGI in-process fallback against the real FastAPI app/routes/services/repos/worker with isolated DB-backed behavior.
- Environment summary:
  - OS: macOS `Darwin 25.3.0`
  - Python: host `3.14.3`, Poetry env `3.12.8`
  - Poetry: `2.3.2`
  - DB: isolated SQLite file
  - Auth mode: recruiter bearer dev token in `TENON_ENV=test`
- Evidence bundle paths:
  - `.qa/issue206/manual_qa_20260309T152525Z/`
  - `.qa/issue206/manual_qa_20260309T152525Z.zip`

| Scenario | Result | Finding |
|---|---|---|
| A | PASS | `POST /api/simulations` returned `201`, `status="generating"`, and non-empty `scenarioGenerationJobId`; DB showed queued `scenario_generation` job. |
| B | PASS | `GET /api/jobs/{job_id}` exposed `jobType="scenario_generation"` with public statuses `queued`, `completed`, and `failed` at runtime. |
| C | PASS | Worker run created/reused `ScenarioVersion v1`, persisted scenario payload, set `active_scenario_version_id`, and transitioned simulation to `ready_for_review`. |
| D | PASS | Seeded tasks were updated from generated prompts; descriptions and rubric-derived scores were applied. |
| E | PASS | Simulation detail exposed `storylineMd`, `taskPromptsJson`, `rubricJson`, and metadata fields. |
| F | PASS | Deterministic fallback was stable for identical `(role, techStack, templateKey)`. |
| G | PASS | Forced generation failure produced failed job status while simulation stayed `generating` with no active scenario version. |
| H | PASS | Controlled retry/re-run did not create duplicate `ScenarioVersion v1` rows. |

- Key evidence files:
  - `.qa/issue206/manual_qa_20260309T152525Z/QA_REPORT.md`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_a_create_simulation_response.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_b_get_job_status_queued_response.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_c_db_assertions.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_d_task_update_comparison.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_e_get_simulation_detail_response.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_f_determinism_assertion.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_g_get_job_status_failed_response.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/scenario_h_retry_idempotency_assertion.json`
  - `.qa/issue206/manual_qa_20260309T152525Z/artifacts/verification_results.json`
- Commands run + results:
  - Localhost `uvicorn` probe -> FAIL (`curl` exit `7`; bind blocked on `127.0.0.1:8016`)
  - ASGI harness run #1 -> FAIL (QA harness query bug: selected non-existent `jobs.completed_at`)
  - ASGI harness run #2 -> FAIL (QA harness JSON normalization bug for `jobs.payload_json`)
  - ASGI harness run #3 -> PASS (scenarios A-H PASS)
  - Bundle secret scan -> PASS (`no_matches`; grep-style scan exit `1` expected when no matches)
  - Bundle zip creation -> PASS
- Notes / limitations:
  - Localhost bind was blocked in sandbox, so QA used ASGI in-process fallback.
  - SQLite was used for isolated runtime QA; Postgres-specific behavior was not directly exercised.
  - Two earlier QA harness attempts failed due QA-script bugs only; final harness pass succeeded.
  - Runtime jobs response uses `jobType` (not `type` from issue prose example), matching current backend schema/runtime.
- Final QA conclusion:
  - Runtime/manual audit evidence is `PASS` for issue #206 scope; create -> generating -> ready lifecycle, job polling visibility, scenario persistence/read-path, deterministic fallback stability, failure semantics, and v1 idempotency were all verified in the evidence bundle.

## Risks / Rollout notes
- Depends on durable jobs contracts from #194 and ScenarioVersion persistence contracts from #205.
- Worker execution is out-of-band in production; simulation stays `generating` until worker completion.
- Public jobs API intentionally abstracts storage-level terminal labels (`succeeded`/`dead_letter`).
- Runtime jobs contract field for job type is `jobType` in current schema/runtime.
- Manual/runtime audit used ASGI in-process + SQLite due sandbox localhost bind restrictions; Postgres-specific behavior was not directly exercised in that run.
- Logging records status/metadata/latency without logging full scenario content or secrets.

## Demo / verification checklist
1. Create a simulation via `POST /api/simulations`.
2. Verify response includes `status="generating"` and `scenarioGenerationJobId`.
3. Run worker or poll `GET /api/jobs/{job_id}` until terminal state.
4. Verify successful generation transitions simulation to `ready_for_review`.
5. Verify simulation detail exposes generated scenario content (`storylineMd`, `taskPromptsJson`, `rubricJson`) and metadata fields.
6. Verify deterministic fallback returns stable output for identical `(role, techStack, templateKey)` tuples.
7. Verify forced generation failure leaves simulation in `generating` and job status as failed.

## Notes / follow-ups
- Regeneration endpoint and approval/send gating continue in adjacent follow-up issues (for example #207 + recruiter approval UX flow).
