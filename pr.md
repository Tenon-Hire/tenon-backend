# Issue #203: GitHub Runtime - Unified Day2/Day3 Workspace + Checkpoint/Final SHA Evidence

## TL;DR

- Day 2 and Day 3 now resolve to one canonical coding workspace/repo per candidate session (`workspace_key="coding"`).
- Day 2 submit now records checkpoint evidence; Day 3 submit now records final evidence.
- Submit responses remain backward compatible and now include additive SHA fields for evaluator/recruiter flows.
- Day 3 init reuses the existing grouped coding workspace and does not create a second repo.

## Problem / Why

Day 2 and Day 3 previously diverged around provisioning/submission evidence handling. The runtime needed one shared repo/workspace for both coding days while preserving separate evidence semantics:

- Day 2 should record checkpoint evidence.
- Day 3 should record final evidence.

This aligns with the candidate experience (single continuous repo/codespace) and recruiter evidence needs (distinct checkpoint vs final SHAs).

## What changed

- Submission persistence now includes nullable `checkpoint_sha` and `final_sha` fields.
- Task submit response now includes additive fields:
  - `commitSha` (canonical evaluation basis)
  - `checkpointSha`
  - `finalSha`
- Day 3 init now reuses the grouped coding workspace from Day 2.
- Day 3 init now returns `WORKSPACE_NOT_INITIALIZED` if the Day 2 coding workspace has not been initialized for that session.
- Provisioning logic prevents duplicate coding repo creation for grouped Day 2/Day 3 sessions.

### Acceptance Criteria Mapping

- Same `repoFullName` for Day 2 and Day 3: satisfied by grouped `coding` workspace resolution.
- Day 2 submit returns `checkpointSha`: satisfied by Day 2 evidence assignment + response mapping.
- Day 3 submit returns `finalSha`: satisfied by Day 3 evidence assignment + response mapping.
- No duplicate repos per session: satisfied by grouped workspace uniqueness and duplicate-create prevention paths.

## API contract notes

- Submit response contract is additive and backward compatible.
- `commitSha` remains canonical for evaluation basis on both days.
- Day 2 submit example:

```json
{
  "submissionId": 555,
  "commitSha": "abc123",
  "checkpointSha": "abc123",
  "finalSha": null,
  "nextTaskId": 777
}
```

- Day 3 submit example:

```json
{
  "submissionId": 556,
  "commitSha": "def456",
  "checkpointSha": null,
  "finalSha": "def456",
  "nextTaskId": 888
}
```

## Migration notes

- Added Alembic revision `202603080003`.
- Revision adds `submissions.checkpoint_sha` and `submissions.final_sha` (nullable).
- Commands run:
  - `poetry run alembic heads` -> PASS (`202603080003 (head)`)
  - `poetry run alembic show 202603080003` -> PASS (revision metadata and dependency chain displayed correctly)
- Sandbox limitation: direct localhost Postgres upgrade validation was unavailable in this environment.
- SQLite migration-chain failure observed during local chain validation is due to a pre-existing historical migration incompatibility, not this revision.

## Tests

- `poetry run pytest -q` -> PASS (`1030 passed in 19.59s`, coverage `99.04%`).
- `poetry run pytest -q tests/api/test_task_submit.py` -> FAIL exit code due coverage threshold only (`12 passed`; repo-wide `--cov-fail-under=99` failed on subset run).
- `poetry run pytest -q --no-cov tests/api/test_task_submit.py` -> PASS (`12 passed in 0.68s`).

Targeted subset coverage-threshold note: the subset failure is only from repo-wide coverage gating (`--cov-fail-under=99`) on partial test selection; functional subset tests pass when run without coverage enforcement (`--no-cov`).

## Audit QA (manual runtime)

**Overall verdict:** `PASS` - Issue #203 is PR-ready from a manual runtime QA perspective.

**Execution method**
- Attempted real localhost startup first: `poetry run uvicorn app.main:app --host 127.0.0.1 --port 8011`.
- Sandbox localhost TCP bind failed with `operation not permitted`.
- Used ASGI in-process fallback harness: `scripts/manual_http_harness.py`.
- Harness exercised real FastAPI app route/service/repository execution paths.
- External GitHub/Actions dependencies were stubbed only where needed for isolation.

**Environment summary**
- Environment capture: `.qa/issue203/manualqa_20260308_155214/env.txt`.
- Runtime DB: SQLite (`db/manualqa_runtime.sqlite`) for deterministic QA.

**Scenario matrix**

| Scenario | Result | Evidence |
|---|---|---|
| A - Day 2 init creates repo | PASS | `.qa/issue203/manualqa_20260308_155214/responses/day2_init.json`, `.qa/issue203/manualqa_20260308_155214/artifacts/verification_results.json` |
| B - Day 3 init reuses same repo | PASS | `.qa/issue203/manualqa_20260308_155214/responses/day2_init.json`, `.qa/issue203/manualqa_20260308_155214/responses/day3_init.json`, `.qa/issue203/manualqa_20260308_155214/db/workspace_groups.json`, `.qa/issue203/manualqa_20260308_155214/db/workspaces.json` |
| C - status/run use same canonical repo | PASS | `.qa/issue203/manualqa_20260308_155214/responses/day2_status.json`, `.qa/issue203/manualqa_20260308_155214/responses/day3_status.json`, `.qa/issue203/manualqa_20260308_155214/responses/day3_run.json`, `.qa/issue203/manualqa_20260308_155214/artifacts/verification_results.json` |
| D - Day 2 submit stores checkpoint SHA | PASS | `.qa/issue203/manualqa_20260308_155214/responses/day2_submit.json`, `.qa/issue203/manualqa_20260308_155214/db/submissions.json`, `.qa/issue203/manualqa_20260308_155214/artifacts/verification_results.json` |
| E - Day 3 submit stores final SHA | PASS | `.qa/issue203/manualqa_20260308_155214/responses/day3_submit.json`, `.qa/issue203/manualqa_20260308_155214/db/submissions.json`, `.qa/issue203/manualqa_20260308_155214/artifacts/verification_results.json` |
| F - submit without init returns `WORKSPACE_NOT_INITIALIZED` | PASS | `.qa/issue203/manualqa_20260308_155214/responses/submit_without_init.json` |
| G - duplicate repo creation prevented | PASS | `.qa/issue203/manualqa_20260308_155214/responses/day2_init_repeat.json`, `.qa/issue203/manualqa_20260308_155214/responses/day3_init_repeat.json`, `.qa/issue203/manualqa_20260308_155214/db/workspace_groups.json`, `.qa/issue203/manualqa_20260308_155214/db/workspaces.json`, `.qa/issue203/manualqa_20260308_155214/artifacts/verification_results.json` |

**Evidence bundle paths**
- QA folder: `.qa/issue203/manualqa_20260308_155214/`
- ZIP: `.qa/issue203/manualqa_20260308_155214.zip`

**Notes / limitations**
- Localhost TCP bind is blocked in this sandbox.
- GitHub network interactions were stubbed for external isolation.
- SQLite was used for deterministic runtime QA.
- Postgres-specific runtime differences were not covered by this QA run.

**Conclusion**
Manual runtime QA for Issue #203 is `PASS`; this change is ready for PR raise from the manual runtime QA perspective.

## Risks / Rollout notes

- SHA assignment is based on current day semantics (Day 2 = checkpoint, Day 3 = final).
- `nextTaskId` behavior was not changed by this issue.
- Recruiter-facing checkpoint/final SHA display is enabled by persistence in this change; downstream read/display surfaces may be addressed separately.

## Demo checklist

- Invite candidate.
- Day 2 init creates repo.
- Day 3 init shows same repo.
- Day 2 submit returns `checkpointSha`.
- Day 3 submit returns `finalSha`.
