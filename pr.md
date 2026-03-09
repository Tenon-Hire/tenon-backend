# Title
Backend: add scenario regenerate vN flow with approval gating and version pinning

## TL;DR
- `POST /api/simulations/{id}/scenario/regenerate` now creates `ScenarioVersion vN` in `status="generating"` and increments `version_index`.
- A durable `scenario_generation` job is queued with `scenarioVersionId` so generation targets an explicit version row.
- Regenerated versions require explicit recruiter approval before invites can proceed.
- Existing candidate sessions stay pinned to their original `scenario_version_id`; new invites after approval use the new active version.
- Regenerate is rate-limited via the repo-standard limiter (current in-memory pattern).

## Problem
Recruiters need deterministic regeneration when a generated scenario is not acceptable, without mutating already-started candidate experiences. Fairness requires version pinning for existing sessions and explicit approval gating before future invites can move to a new scenario version.

## What changed

### API
- Added `POST /api/simulations/{id}/scenario/regenerate`.
- Added `POST /api/simulations/{id}/scenario/{scenario_version_id}/approve`.
- `GET /api/simulations/{id}` now includes:
  - `activeScenarioVersionId`
  - `pendingScenarioVersionId`

Regenerate response contract:

```json
{
  "scenarioVersionId": 12,
  "jobId": "0f3f2c1e-...",
  "status": "generating"
}
```

### State model / lifecycle
- `Simulation.active_scenario_version_id` remains the invite source of truth.
- `Simulation.pending_scenario_version_id` stages regenerated versions awaiting approval.
- Regeneration flow:
  - create vN as `generating`
  - worker marks vN `ready` on completion
  - recruiter approval promotes vN to active and clears pending
- Simulation remains non-invitable while pending approval exists; invite/activate attempts return `SCENARIO_APPROVAL_PENDING`.

### Worker / job behavior
- Scenario generation jobs now target a specific `scenarioVersionId` in payload, not implicit "latest version" behavior.
- The handler updates that exact scenario version and marks it `ready` when generation completes.
- This keeps regeneration deterministic and retry-safe per version row.

### Invite pinning
- Existing candidate sessions remain pinned to their original `scenario_version_id`.
- Regeneration is allowed with active sessions; no silent mutation occurs for in-flight candidates.
- After approval, new invites pin to the newly active scenario version.

### Rate limiting
- Regenerate endpoint uses the repo-standard limiter (`RateLimitRule` + `rate_limit.limiter.allow`).
- Scope follows existing in-memory limiter behavior (user/client keyed).
- This is acceptable for current MVP scope.

## Data model / migration
- Added `Simulation.pending_scenario_version_id` (FK to `scenario_versions.id`).
- Updated `scenario_versions` status check constraint to include `generating`.
- Migration: `alembic/versions/202603090002_add_pending_scenario_version_and_generating_status.py`.

## Deleted / cleaned up
- Removed obsolete duplicate route modules:
  - `app/api/routers/simulations_routes/scenario_regenerate.py`
  - `app/api/routers/simulations_routes/scenario_update.py`
- Routing is now consolidated in `app/api/routers/simulations_routes/scenario.py`.
- This avoids duplicate/ambiguous route registration; route uniqueness is covered by tests.

## Error contracts
Verified key contracts:
- `409 SCENARIO_REGENERATION_PENDING`
- `409 SCENARIO_APPROVAL_PENDING`
- `409 SCENARIO_NOT_READY`
- `403` owner-only protection
- `404` simulation/version not found
- `429` regenerate rate-limited

## Testing
Authoritative gate:
- `./precommit.sh` -> PASS
- Total tests: `1127 passed`
- Coverage: `99.05%`
- Manual runtime QA: `PASS` (evidence-backed)
- QA bundle:
  - `.qa/issue207/manual_qa_20260309T224125Z`
  - `.qa/issue207/manual_qa_20260309T224125Z.zip`

Covered behavior categories:
- regenerate flow (vN creation + queueing + worker completion)
- approval gating
- invite blocking while pending approval
- existing session pinning
- post-approval new invite uses new active version
- regenerate rate-limit behavior
- route uniqueness for scenario endpoints
- simulation detail contract transitions (`activeScenarioVersionId` / `pendingScenarioVersionId`)

## Manual QA
- Completed against the real FastAPI app (`app.main:app`) using ASGI in-process fallback after localhost bind was blocked by sandbox restrictions.
- Exercised real HTTP routes and real DB-backed logic for regenerate/pending/approve/pinning flow.
- External GitHub/email integrations were stubbed narrowly to avoid network calls.
- Verified scenarios A-L with evidence:
  - A: baseline simulation state
  - B: existing invite/session pinned to v1
  - C: regenerate creates v2 `generating` + targeted job payload (`scenarioVersionId`)
  - D: duplicate regenerate blocked (`409 SCENARIO_REGENERATION_PENDING`)
  - E: pending version blocks new invites (`409 SCENARIO_APPROVAL_PENDING`)
  - F: worker completes v2 to `ready` without activation
  - G: explicit approval promotes v2 to active and clears pending
  - H: new invite after approval uses v2 while old session remains on v1
  - I: approve-before-ready returns `409 SCENARIO_NOT_READY`
  - J: auth negative paths return expected `403` / `404`
  - K: regenerate rate limit returns `429`
  - L: runtime route surface sanity
- Key QA IDs observed: `simulationId=1`, `v1=1`, `v2=2`, `v3=3`, `inviteSessionV1=1`, `inviteSessionV2=2`, `regenJobId=95e3ebd6-8cb0-409e-a2c6-7713a36045f5`.
- Evidence bundle:
  - `.qa/issue207/manual_qa_20260309T224125Z`
  - `.qa/issue207/manual_qa_20260309T224125Z.zip`

### QA notes / limitations
- Localhost runtime was attempted first, but sandbox bind restrictions blocked that path.
- Verification used an isolated SQLite database scoped to QA runs.
- GitHub/email dependencies were stubbed only where needed to avoid external network calls.

## Risks / notes
- Regenerate limiter uses the current in-memory repo pattern (not distributed/shared state).
- No behavior change for already-started sessions beyond preserving pinning fairness.
- Generation completion alone does not activate invites; recruiter approval is still required.

## Rollout / demo checklist
1. Create simulation with v1.
2. Invite candidate A and confirm session is pinned to v1.
3. Regenerate and confirm v2 is created in `generating` and `pendingScenarioVersionId` is set.
4. Complete generation and confirm v2 is `ready` while simulation remains non-invitable.
5. Approve v2.
6. Invite candidate B and confirm session is pinned to v2.
7. Verify candidate A remains pinned to v1.
