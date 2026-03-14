## 1. Title
P2 GitHub Ops: Retention cleanup job for workspace repos + collaborator revocation enforcement (#216)

## 2. TL;DR
- Added durable job type `workspace_cleanup` and wired it into the worker.
- Cleanup execution order is explicit: collaborator revocation enforcement runs before retention cleanup.
- Retention cleanup archives repos by default; delete is allowed only with explicit destructive opt-in.
- Cleanup/revocation lifecycle state is canonical on `WorkspaceGroup` for grouped repos.
- Legacy `Workspace` lifecycle fields remain for compatibility/fallback for ungrouped rows.
- No new public endpoint was added.

## 3. Problem / Why
Workspace repos and collaborator access can outlive their useful lifecycle when cleanup/revocation is not enforced durably. That creates avoidable GitHub footprint/cost and lingering access risk. Issue #216 adds durable, idempotent cleanup + revocation enforcement with explicit safety controls.

## 4. What changed
- Job foundation integration:
  - Added durable job type `workspace_cleanup`.
  - Added enqueue/idempotency helpers in `app/services/submissions/workspace_cleanup_jobs.py`.
  - Added worker handler `handle_workspace_cleanup` in `app/jobs/handlers/workspace_cleanup.py` and registered it in worker/handler registry.
- Cleanup/revocation runtime behavior:
  - Revocation enforcement executes first for targets that require it.
  - Retention cleanup executes afterward when eligible and expired.
  - Structured logging emits start/success/failure events for revocation and archive/delete operations.
- GitHub integration:
  - Added archive/delete repo client operations used by cleanup handler.
  - Existing collaborator removal is reused for revocation enforcement.
- Persistence/model updates:
  - Added cleanup/revocation lifecycle columns on `workspace_groups` (canonical for grouped repos).
  - Added/retained lifecycle columns on `workspaces` for compatibility/fallback ungrouped rows.
  - Added migrations for both tables.
- Config added:
  - `TENON_WORKSPACE_RETENTION_DAYS`
  - `TENON_WORKSPACE_CLEANUP_MODE`
  - `TENON_WORKSPACE_DELETE_ENABLED`

## 5. Behavior / semantics
- Revocation is required when cutoff/day-close evidence exists (session present in day-audit evidence set).
- Collaborator revocation runs before any archive/delete action.
- Terminal revocation failure blocks cleanup for that target.
- Transient GitHub failures are retryable and bubble to durable worker retry path.
- Active sessions are skipped.
- Retention anchor uses `candidate_session.completed_at` when present; otherwise repo record `created_at`.
- Grouped and legacy duplicate references are deduped by candidate-session + repo identity.
- Already-cleaned targets are a no-op on rerun (idempotent behavior).
- Cleanup mode defaults to archive.
- Delete requires both:
  - `TENON_WORKSPACE_CLEANUP_MODE=delete`
  - `TENON_WORKSPACE_DELETE_ENABLED=true`

## 6. Files changed
- Job enqueue + idempotency:
  - `app/services/submissions/workspace_cleanup_jobs.py`
- Worker handler + registration:
  - `app/jobs/handlers/workspace_cleanup.py`
  - `app/jobs/handlers/__init__.py`
  - `app/jobs/worker.py`
- GitHub client:
  - `app/integrations/github/client/repos.py`
- Settings/config:
  - `app/core/settings/github.py`
  - `app/core/settings/settings.py`
  - `app/core/settings/merge.py`
  - `.env.example`
- Data model + migrations:
  - `app/repositories/github_native/workspaces/models.py`
  - `alembic/versions/202603130002_add_workspace_cleanup_state_columns.py`
  - `alembic/versions/202603130003_add_workspace_group_cleanup_state_columns.py`
- Tests:
  - `tests/unit/test_workspace_cleanup_handler.py`
  - `tests/integration/test_workspace_cleanup_job_integration.py`
  - `tests/unit/test_workspace_cleanup_jobs.py`
  - `tests/unit/test_workspace_cleanup_migrations_smoke.py`
  - `tests/unit/test_github_client.py`
  - `tests/unit/test_job_handler_registration.py`

## 7. Testing
- Repo quality gate passed.
- `./precommit.sh` passed.
- Total coverage reached `99.01%`.
- Migration smoke test passed.

Representative high-signal test coverage includes:
- Active-session skip behavior.
- Revocation hard-stop behavior on terminal failures.
- Rerun idempotency behavior.
- Canonical grouped-state handling with duplicate legacy reference skip.
- Archive and delete worker flows.
- Transient revocation failure retry behavior.

## 8. Manual QA / Runtime Verification
### Runtime method
- Real localhost backend:
  - `poetry run uvicorn app.api.main:app --host 127.0.0.1 --port 8000`
- Real Postgres database:
  - `tenon_issue216_20260313t221241z`
- Real durable worker path:
  - `app.jobs.worker.run_once`
- GitHub boundary:
  - local HTTP stub via `TENON_GITHUB_API_BASE=http://127.0.0.1:9100`

The Tenon backend/runtime/DB were real. GitHub operations were isolated behind a deterministic local stub.

### Evidence path
- `.qa/issue216/manual_qa_20260313T221241Z`

Evidence bundle contains:
- `report.md`
- `commands.log`
- `server.log`
- `worker.log`
- `db_scenario_*.sql`
- `db_scenario_*_output.txt`
- `github_stub_calls.jsonl`
- `seed_summary.json`

### Scenario summary
All scenarios A-H passed:
- **A** — archive success with revocation-before-cleanup
- **B** — delete success with explicit opt-in
- **C** — delete guard blocks destructive cleanup
- **D** — active session is skipped
- **E** — terminal revocation failure blocks cleanup
- **F** — transient revocation failure retries safely, then succeeds
- **G** — idempotent rerun is a no-op
- **H** — canonical grouped repo state is used and duplicate legacy reference is skipped

### Strongest proof points
- Scenario A showed `remove_collaborator` before `archive_repo`.
- Scenario B showed delete only when `TENON_WORKSPACE_DELETE_ENABLED=true`.
- Scenario C showed no delete call with guard disabled.
- Scenario D showed old but active sessions remain `pending`.
- Scenario E showed terminal revocation failure prevents cleanup.
- Scenario F showed retry-safe behavior after transient `502`.
- Scenario H showed lifecycle state on `workspace_groups` while legacy duplicate `workspaces` row remained untouched.

### Final QA verdict
- **Manual runtime QA verdict: PASS**
- **Issue #216 is PR-ready from a runtime QA perspective**

## 9. Security / safety notes
- Cleanup scope is DB-backed workspace records only; non-workspace repos are not targeted.
- Delete is guarded by explicit config opt-in (`TENON_WORKSPACE_DELETE_ENABLED=true`).
- Archive remains the default cleanup mode.
- Revocation-before-cleanup ordering reduces residual collaborator access risk.
- Logs are structured for observability and avoid token/secret leakage.
- No new public endpoint was introduced.

## 10. Risks / follow-ups
- Periodic scheduling wiring (cron/scheduler trigger policy) remains operational follow-up beyond this implementation.
- Legacy `Workspace` lifecycle columns are intentionally retained for compatibility/fallback while grouped canonical state resides on `WorkspaceGroup`.

## 11. Rollout / demo checklist
1. Seed/create candidate workspace repos tied to candidate sessions.
2. Ensure cutoff/day-close evidence is present for revocation-required scenarios.
3. Run durable `workspace_cleanup` job for the target company.
4. Verify collaborator revocation execution and persisted lifecycle fields.
5. Verify retention behavior under default archive mode.
6. Verify delete behavior only with explicit delete mode + guard enabled.
7. Rerun the job and verify idempotent no-op for already-cleaned targets.
8. Verify grouped canonical behavior and legacy duplicate skip behavior.

## 12. Final status
Implementation complete, automated checks green, and runtime QA evidence recorded.

Issue #216 is PR-ready.
