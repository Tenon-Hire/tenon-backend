## 1. Title
P1 Demo Ops: Admin endpoints for candidate session reset, job requeue, and simulation fallback scenario (#219)

## 2. TL;DR
- Shipped three demo-ops admin endpoints under `/api/admin/*`:
  - `POST /api/admin/candidate_sessions/{candidate_session_id}/reset`
  - `POST /api/admin/jobs/{job_id}/requeue`
  - `POST /api/admin/simulations/{simulation_id}/scenario/use_fallback`
- Added centralized demo/admin gating dependency:
  - demo mode off => `404`
  - demo mode on + non-admin => `403`
- Added `admin_action_audits` table + migration and wired audit writes for all admin actions.
- Enforced constrained, auditable, idempotent behavior with explicit `409` unsafe-operation semantics.

## 3. Why / problem
Demo operations needed safe recovery paths for three failure classes: wedged candidate sessions, stuck jobs, and unusable scenario versions. The required capability is to recover without arbitrary DB mutation, preserve auditability, and avoid changing locked or already-pinned candidate scenario assignments.

## 4. What changed
- Centralized demo-mode + admin gating:
  - Added `require_demo_mode_admin` in `app/api/dependencies/admin_demo.py`.
  - Gating behavior is centralized and reused by all demo-ops endpoints.
  - Admin auth supports both paths:
    - claim path (`role=admin` or `tenon_roles`/roles-derived admin claim)
    - allowlist path (email, subject, recruiter_id config allowlists)
- Audit model/migration:
  - Added `admin_action_audits` model/repository and migration `202603150001_add_admin_action_audits.py`.
  - All admin ops write sanitized payloads (reason/flags/ids/status metadata only).
- Reset endpoint:
  - Implemented constrained state reset for candidate sessions via `reset_candidate_session`.
  - Evaluated-session resets without override are blocked with `409 UNSAFE_OPERATION`.
  - Supports dry-run validation mode without mutation/audit row writes.
- Requeue endpoint:
  - Implemented `requeue_job` for safe status transitions back to `queued`.
  - Supports no-op idempotent requeue when already queued.
  - Enforces stale-running/dead-letter safety checks when `force=false`; unsafe paths return `409`.
- Fallback scenario endpoint:
  - Implemented simulation-level fallback switch to active scenario for future invites only.
  - Prevents unsafe fallback when simulation is terminated, scenario is ineligible, or approval is pending (`409`).
  - Preserves existing invited-session pinning; only future invites use the switched active scenario.
  - Iteration 2 bugfix: dry-run fallback path captures the resolved `scenarioVersionId` before rollback so dry-run response is correct and deterministic.

## 5. API contracts
- `POST /api/admin/candidate_sessions/{candidate_session_id}/reset`
  - Request: `targetState`, `reason`, `overrideIfEvaluated=false` (default), `dryRun=false` (default)
  - Response: `candidateSessionId`, `status` (`ok|dry_run`), `resetTo`, `auditId` (`null` on dry-run)
  - Errors: `404` (demo off/target missing), `403` (not admin), `409` (`UNSAFE_OPERATION` for evaluated reset without override or invalid safe-reset conditions)
- `POST /api/admin/jobs/{job_id}/requeue`
  - Request: `reason`, `force=false` (default)
  - Response: `jobId`, `previousStatus`, `newStatus`, `auditId`
  - Errors: `404` (demo off/target missing), `403` (not admin), `409` (`UNSAFE_OPERATION` for unsafe requeue without `force`, or invalid force path)
- `POST /api/admin/simulations/{simulation_id}/scenario/use_fallback`
  - Request: `scenarioVersionId`, `applyTo` (`future_invites_only`), `reason`, `dryRun=false` (default)
  - Response: `simulationId`, `activeScenarioVersionId`, `applyTo`, `auditId` (`null` on dry-run)
  - Errors: `404` (demo off/missing objects), `403` (not admin), `409` (`UNSAFE_OPERATION` for ineligible fallback state, `SCENARIO_APPROVAL_PENDING` when pending scenario exists)

## 6. Safety / security decisions
- Demo mode is disabled by default (`TENON_DEMO_MODE` / `settings.DEMO_MODE` defaults false).
- Access is guarded by both demo-mode and admin checks.
- Admin authorization supports claim-based and allowlist-based paths.
- Audit payloads are sanitized and do not store candidate PII fields (no candidate email/video/transcript payload data).
- Endpoints expose constrained operations only; no arbitrary DB mutation interface was added.
- Fallback switch does not mutate locked scenario content.
- Already invited sessions are not rebound to a different scenario version.

## 7. Idempotency behavior
- Requeueing an already `queued` job is a no-op `200` and leaves status unchanged.
- Applying fallback with the same active scenario version is a no-op `200`.
- Dry-run reset/fallback paths validate and return intent without mutating state or writing audit rows.

## 8. Data model / migration notes
- Added `admin_action_audits` table with:
  - `id`, `actor_type`, `actor_id`, `action`, `target_type`, `target_id`, `payload_json`, `created_at`
- Migration: `alembic/versions/202603150001_add_admin_action_audits.py`
- Added indexes:
  - `ix_admin_action_audits_created_at`
  - `ix_admin_action_audits_action_created_at`

## 9. Tests and validation
- Final quality gate:
  - `./precommit.sh` -> PASS
  - `1500 passed`
  - total coverage `99.02%` (coverage gate >=99% satisfied)
  - `app/services/admin_ops_service.py` -> `100%`
- Targeted integration coverage includes:
  - demo-mode off returns `404`
  - non-admin in demo mode returns `403`
  - reset endpoint audit write + evaluated-session `409` block + dry-run non-mutation
  - requeue flow from dead-letter to queued with worker processing to succeeded
  - fallback switch for future invites with existing sessions staying pinned
- Targeted unit coverage includes:
  - admin dependency auth paths (claim + allowlist variants)
  - stale-running and force requeue safety matrix
  - fallback pending/ineligible/terminated `409` conditions
  - sanitized audit payload behavior

## 10. Manual QA / Runtime Verification
- Verdict: PASS.
- Runtime method:
  - Real localhost FastAPI server on `127.0.0.1:8019`.
  - Fresh dedicated Postgres DB: `tenon_issue219_manualqa_20260315t021621z`.
  - Migration command used:
    - `TENON_ENV=test TENON_DATABASE_URL=<async> TENON_DATABASE_URL_SYNC=<sync> poetry run alembic upgrade head`
    - Succeeded through head including revision `202603150001`.
  - Real HTTP calls to admin endpoints, direct Postgres verification (before/after snapshots), and real worker execution through the `app.jobs.worker.run_once` code path.
- Evidence bundle:
  - `.qa/issue219/manual_qa_20260315T021621Z/`
  - Pointer file: `.qa/issue219/LATEST_EVIDENCE_PATH.txt`
- Repo state during QA:
  - Before QA: clean (`git status --short` empty).
  - After QA: clean (`git status --short` empty).
  - No tracked product files changed during QA.
- Scenario summary:
  - Demo mode / auth gating:
    - Demo mode off: all three admin endpoints returned `404`.
    - Demo mode on + non-admin: all three admin endpoints returned `403`.
  - Reset endpoint:
    - Dry-run returned `200` with no DB mutation and no audit row.
    - Evaluated session reset without override returned `409`.
    - Successful reset returned `200`, safely rewound session state, and inserted an audit row.
  - Requeue endpoint:
    - Unsafe fresh-running job returned `409`.
    - Dead-letter job requeue returned `200`, transitioned to `queued`, and real worker execution completed it to `succeeded`.
    - Queued-job requeue was a no-op `200`.
    - Observed behavior: queued no-op requeue still writes an audit row.
  - Fallback scenario endpoint:
    - Dry-run returned `200` with no mutation and no audit row.
    - Successful fallback switched simulation active scenario for future invites only.
    - Existing invited session remained pinned to the old scenario version.
    - New invite created after fallback pinned to the new scenario version.
    - Pending-approval fallback attempt returned `409`.
  - Audit payload sanitization:
    - Verified sanitized payloads in Postgres audit rows.
    - No candidate email / invite email / transcript / video / URL-like sensitive values found in inspected payloads.
- Strongest proof points:
  - Real HTTP calls proved endpoint hiding and admin authorization behavior (`404` / `403`).
  - Reset safety was proven with dry-run non-mutation, evaluated-session `409`, and successful reset audit insertion.
  - Requeue was proven end-to-end: admin API requeue -> `queued` -> real worker run -> `succeeded`.
  - Fallback semantics were proven for future-invites-only behavior: existing invited session stayed pinned while a new invite pinned to the fallback scenario.
  - Audit payload sanitization was verified directly in Postgres.

## 11. Risks / follow-ups
- Optional session-level fallback endpoint (`/api/admin/candidate_sessions/{id}/scenario/use_fallback`) is intentionally deferred and not part of this PR.
- Existing repo-wide limitation remains: full historical `alembic upgrade head` on SQLite can fail at an older unrelated migration; this issue’s migration is not the source of that limitation.

## 12. Rollout / demo checklist
1. Force a demo job into a stuck/failed state and call requeue endpoint; verify it returns to `queued` and worker completes it.
2. Switch a simulation to a known-good fallback scenario using `future_invites_only`; verify new invites pin to fallback and previously invited sessions remain pinned.
3. Reset a wedged demo candidate session using constrained target state and verify it can proceed again.

## 13. Notes for reviewers
- Canonical router path is under `app/api/routers/admin_routes/*`.
- Duplicate shim files under `app/api/routes/admin_routes/*` were removed; no parallel admin-routes shim path remains.
