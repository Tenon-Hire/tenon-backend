# P0 Recruiter Core: Terminate Simulation (idempotent) + invite blocking + cleanup job orchestration

## TL;DR

- Added recruiter-only `POST /api/simulations/{simulation_id}/terminate` with explicit confirmation and optional reason.
- Termination is idempotent: repeated calls return `200`, keep the original `terminatedAt`, and return stable `cleanupJobIds`.
- Termination transitions simulation state to `terminated` and persists termination metadata (`terminated_at`, `terminated_reason`, `terminated_by_recruiter_id`).
- Invite create and resend are both blocked after termination with `409` + `errorCode=SIMULATION_TERMINATED`.
- Candidate-facing surfaces hide terminated simulations by default (invite lists, token resolve, claim, owned-session fetch).
- Cleanup is orchestrated via durable jobs: `simulation_cleanup` jobs are enqueued with simulation-scoped payload and idempotency key.
- Worker registration for cleanup is explicit at startup (`register_builtin_handlers()`), not via import-time side effects.

## API Contract

- Endpoint: `POST /api/simulations/{simulation_id}/terminate`
- Auth: recruiter bearer token + owner-only simulation access.
- Request:

```json
{ "confirm": true, "reason": "regenerate" }
```

- Response (example):

```json
{
  "simulationId": 42,
  "status": "terminated",
  "terminatedAt": "2026-03-02T16:30:00Z",
  "cleanupJobIds": ["0f3f2c1e-8f2d-4a6a-9c1a-2a3b4c5d6e7f"]
}
```

- Error cases:
- `403` when requester is not the owner.
- `404` when simulation does not exist.
- `400` when `confirm` is missing/false (`SIMULATION_CONFIRMATION_REQUIRED`).
- `409` on invite create/resend against a terminated simulation (`SIMULATION_TERMINATED`).

## Behavior / Acceptance Criteria Mapping

- AC: Cannot create or resend invites after termination (`SIMULATION_TERMINATED`).
- Implemented via `require_simulation_invitable()` in both invite routes before invite side effects; verified by:
- `tests/api/test_simulations_lifecycle.py::test_invite_create_blocked_after_termination`
- `tests/api/test_simulations_lifecycle.py::test_invite_resend_blocked_after_termination`

- AC: Candidate dashboard does not show terminated simulations.
- Implemented with default `include_terminated=False` filtering in candidate invite listing and terminated-token hiding; verified by:
- `tests/api/test_simulations_lifecycle.py::test_candidate_invites_hide_terminated_by_default`
- `tests/api/test_simulations_lifecycle.py::test_candidate_token_resolve_and_claim_hidden_after_termination`

- AC: Termination enqueues cleanup job(s) and returns job IDs.
- `terminate_simulation_with_cleanup()` enqueues `simulation_cleanup` and response includes `cleanupJobIds`; verified by:
- `tests/api/test_simulations_lifecycle.py::test_terminate_is_owner_only_and_idempotent`
- `tests/unit/test_simulations_lifecycle_service.py::test_terminate_with_cleanup_sets_reason_and_enqueues_job`

- AC: Endpoint is idempotent.
- Repeated terminate calls return `200` with `status=terminated`, same `terminatedAt`, and same `cleanupJobIds`; single persisted cleanup job is reused through idempotency key dedupe.

## Implementation Details

- State transition:
- `apply_status_transition(..., target_status="terminated")` sets `simulation.status -> terminated` and sets `terminated_at` once.
- On first transition only, service persists `terminated_reason` and `terminated_by_recruiter_id`.

- Invite guards (early, before side effects):
- `invite_create.py` and `invite_resend.py` call `require_simulation_invitable(simulation)` before invite creation/resend logic, preventing downstream email/GitHub side effects when terminated.

- Candidate hiding strategy:
- Token path returns `404` with `"Invalid invite token"` for terminated simulations (`fetch_token.py`).
- Owned-session and token fetch paths filter terminated simulations at query level via joined simulation-status predicate (`repository_basic.py` and `repository_tokens.py`).
- Defense-in-depth fail-closed guards reject access when simulation relationship is missing/unloaded (`fetch_owned_helpers.py`, `fetch_token.py`).

- Cleanup job orchestration:
- Job type: `simulation_cleanup`.
- Idempotency key: `simulation_cleanup:{simulation_id}`.
- Payload includes `simulationId` (plus `companyId`, `terminatedByUserId`, optional `reason`).
- Job creation uses `create_or_get_idempotent(..., commit=False)` so enqueue participates in the same transaction as termination.
- Handler registration is explicit at worker startup (`app/jobs/worker.py::register_builtin_handlers`), with no import-time registration side effects.

- Concurrency note:
- Candidate-session locking is scoped to candidate session rows only (`with_for_update(of=CandidateSession)`), not simulations.
- Compiled SQL proof:

```sql
... FOR UPDATE OF candidate_sessions
```

## Tests

- Commands run:
- `poetry run ruff check .` -> passed (no lint violations).
- `poetry run ruff format .` -> passed (`745 files left unchanged`).
- `poetry run pytest -q` -> passed (`900 passed in 16.01s`).

- Key tests added/updated for this feature:
- `tests/api/test_simulations_lifecycle.py::test_terminate_is_owner_only_and_idempotent`
- `tests/api/test_simulations_lifecycle.py::test_invite_create_blocked_after_termination`
- `tests/api/test_simulations_lifecycle.py::test_invite_resend_blocked_after_termination`
- `tests/api/test_simulations_lifecycle.py::test_terminated_hidden_by_default_in_simulation_and_candidate_lists`
- `tests/api/test_simulations_lifecycle.py::test_candidate_invites_hide_terminated_by_default`
- `tests/api/test_simulations_lifecycle.py::test_candidate_token_resolve_and_claim_hidden_after_termination`
- `tests/unit/test_simulations_lifecycle_service.py::test_terminate_with_cleanup_sets_reason_and_enqueues_job`
- `tests/unit/test_candidate_sessions_repository.py::test_get_by_id_for_update_locks_only_candidate_sessions`
- `tests/unit/test_candidate_sessions_repository.py::test_get_by_token_for_update_locks_only_candidate_sessions`
- `tests/unit/test_job_handler_registration.py::test_register_builtin_handlers_is_explicit`

## Risks / Rollout Notes

- Cleanup is currently best-effort and safe: handler is a retry-safe noop skeleton scoped to simulation-owned resources, so external deletion coverage can be expanded incrementally.
- Idempotent job creation (`simulation_cleanup:{simulation_id}`) prevents duplicate destructive work under retries/races.
- Shared template repositories are protected by scope and current cleanup behavior (no destructive delete path in current handler).

## Demo / Verification Checklist

1. Create simulation -> activate -> invite candidate.
2. Call `POST /api/simulations/{id}/terminate` with `{ "confirm": true }`.
3. Verify invite create returns `409` with `errorCode=SIMULATION_TERMINATED`.
4. Verify invite resend returns `409` with `errorCode=SIMULATION_TERMINATED`.
5. Verify candidate token resolve/claim returns `404` with `"Invalid invite token"` and candidate invite list hides the terminated simulation by default.
6. Verify cleanup job row exists with `job_type=simulation_cleanup`, payload `simulationId={id}`, and returned `cleanupJobIds` contains that job ID.
7. Call terminate again and verify `200` idempotent response with unchanged `terminatedAt` and unchanged `cleanupJobIds`.
