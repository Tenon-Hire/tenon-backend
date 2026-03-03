# P0 Recruiter Core: Simulation lifecycle state machine + invite gating

## TL;DR

- Added a persisted simulation lifecycle with enforced state transitions: `draft -> generating -> ready_for_review -> active_inviting`, plus `any -> terminated`.
- Added owner-only lifecycle APIs for activation and termination, both confirmation-gated and idempotent, to support safe recruiter control in MVP1.1.
- Added invite gating so candidate invites and invite resends are blocked unless the simulation is `active_inviting`.
- Updated simulation and candidate list behavior to hide `terminated` by default, with explicit `includeTerminated=true` opt-in.
- Expanded simulation API responses to include lifecycle status/timestamps and `scenarioVersionSummary`, enabling recruiter review and frontend lifecycle UI.

## Detailed changes

### Database

- Added simulation lifecycle persistence in `simulations`:
  - `status` (non-null, default `generating`)
  - `generating_at`
  - `ready_for_review_at`
  - `activated_at`
  - `terminated_at`
- Backfilled existing `simulations` rows to `active_inviting` and set `activated_at` with `COALESCE(activated_at, created_at, CURRENT_TIMESTAMP)`.
- Added DB CHECK constraint `ck_simulations_status_lifecycle` restricting `status` to:
  - `draft`
  - `generating`
  - `ready_for_review`
  - `active_inviting`
  - `terminated`

### Backend services

- Centralized lifecycle transition rules in simulation lifecycle service:
  - Allowed transitions: `draft -> generating`, `generating -> ready_for_review`, `ready_for_review -> active_inviting`.
  - Termination rule: `any valid status -> terminated`.
- Implemented idempotent transition behavior for `activate` and `terminate`:
  - Repeated requests return success and preserve original lifecycle timestamp.
- Added `normalize_simulation_status` and `normalize_simulation_status_or_raise`:
  - Maps legacy `active` to `active_inviting`.
  - Strictly rejects unknown statuses with `SIMULATION_STATUS_INVALID`.
- Added lifecycle transition logging for successful transitions and rejected attempts, including simulation and actor identifiers.

### API

- New endpoints:
  - `POST /api/simulations/{id}/activate`
    - Requires `{ "confirm": true }`
    - Recruiter owner-only
    - Idempotent
    - Returns `simulationId`, `status`, `activatedAt`
  - `POST /api/simulations/{id}/terminate`
    - Requires `{ "confirm": true }`
    - Recruiter owner-only
    - Idempotent
    - Returns `simulationId`, `status`, `terminatedAt`
- Invite gating:
  - `POST /api/simulations/{id}/invite` now returns `409` with `SIMULATION_NOT_INVITABLE` unless status is `active_inviting`.
  - Invite resend flow enforces the same invitable-state check.
- Filtering behavior:
  - Recruiter simulation list hides terminated simulations by default; `includeTerminated=true` opts in.
  - Recruiter candidate list for a simulation also hides terminated simulations by default; `includeTerminated=true` opts in.
  - Candidate inbox (`GET /api/candidate/invites`) hides terminated simulations by default; `includeTerminated=true` can include them.
- Response schema updates:
  - Simulation create/list/detail responses now include lifecycle status and timestamps.
  - Simulation create/detail include `generatingAt`, `readyForReviewAt`, `activatedAt`, `terminatedAt`.
  - Simulation create/list/detail include `scenarioVersionSummary`.

### Error contracts

- Non-owner lifecycle transitions return `403`.
- Missing simulation returns `404`.
- Invalid persisted status (defensive, should be unreachable with DB constraint) raises `500` with `errorCode: SIMULATION_STATUS_INVALID`.

## Testing

Commands run and results:

- `poetry run ruff check .` -> pass
- `poetry run ruff format .` -> pass (`736 files left unchanged`)
- `poetry run pytest` -> pass (`864 passed in 13.87s`)
- `./precommit.sh` -> pass (`864 passed in 14.07s`, all checks passed)

Additional note:

- `poetry run mypy --version` -> not available (`Command not found: mypy`), so mypy was not run.

## Migration / rollout notes

- Apply migration:
  - `poetry run alembic upgrade head`
- Migration behavior:
  - Adds lifecycle timestamp columns (`generating_at`, `ready_for_review_at`, `activated_at`, `terminated_at`).
  - Backfills existing simulations to `active_inviting` with `activated_at` populated.
  - Enforces status validity via CHECK constraint.

### Demo rollout checklist

1. Create simulation -> status transitions through `generating` to `ready_for_review` (creation path is synchronous, so `generating` may be transient).
2. Activate simulation -> status becomes `active_inviting`, `activatedAt` is set.
3. Invite candidate -> succeeds only after activation.
4. Terminate simulation -> invites become blocked; terminated simulation is excluded from default lists/inbox.

### Rollback

- Use repo downgrade conventions (e.g., `poetry run alembic downgrade -1` for this migration).
- Downgrade removes lifecycle CHECK constraint and drops lifecycle timestamp columns, and restores previous `status` column nullability/default behavior.

## Risks / follow-ups

- #197: termination cleanup orchestration is a follow-up and not completed in this scope.
- #205: deeper scenario version persistence/locking continues in follow-up work.
- #196 and frontend lifecycle UX issues remain complementary tracks.
- Scenario generation is still synchronous in create today, so `generating` can be short-lived/transient in practice.
