# Issue #201: Server-backed task drafts + day-close finalization (Day 1/Day 5 text tasks)

## TL;DR

- Added server-backed task draft persistence (`task_drafts`) and candidate draft endpoints for Day 1/Day 5 text workflows.
- Implemented `GET /api/tasks/{task_id}/draft` and `PUT /api/tasks/{task_id}/draft` with candidate auth, owned-session enforcement, and payload-size guards.
- Added day-close finalization job type (`day_close_finalize_text`) that finalizes canonical submissions at cutoff even if candidate never clicks Submit.
- Schedule-set flow now enqueues deterministic day-close jobs for Day 1 + Day 5 text tasks at `next_run_at=window_end` using idempotency key `day_close_finalize_text:{session_id}:{task_id}`.
- Finalization is idempotent and wedge-safe: existing submissions are no-op, nonterminal requeue is rowcount-aware, and worker verifies handler reschedule disposition before considering the run successful.

## What changed (detailed)

- Data model:
  - Added `task_drafts` table keyed by unique `(candidate_session_id, task_id)` with finalized metadata (`finalized_at`, `finalized_submission_id`).
  - Added `submissions.content_json` (internal-only) for structured draft payloads and no-content cutoff marker.
  - Added migrations:
    - `alembic/versions/202603050002_add_task_drafts_table.py`
    - `alembic/versions/202603050003_add_submission_content_json.py`

- API:
  - Added `GET /api/tasks/{task_id}/draft`.
  - Added `PUT /api/tasks/{task_id}/draft`.
  - Window enforcement uses Option A for writes: outside active window returns `409 TASK_WINDOW_CLOSED`.
  - Additional draft API error contracts:
    - `404 DRAFT_NOT_FOUND`
    - `409 DRAFT_FINALIZED`
    - `413 DRAFT_CONTENT_TOO_LARGE`
  - Auth/ownership requirements are enforced via candidate auth + required `x-candidate-session-id` header + owned-session and task ownership checks.

- Jobs:
  - Added job type `day_close_finalize_text` and worker handler.
  - Jobs are enqueued when schedule is set for Day 1 and Day 5 text tasks with:
    - `next_run_at = window_end`
    - `idempotency_key = day_close_finalize_text:{session_id}:{task_id}`
  - Finalization outcomes:
    - Existing submission present: no-op (and draft linkage finalized if needed).
    - No submission + draft exists: create submission from draft text/json.
    - No submission + no draft: create empty-marker submission with:
      - `content_text = ""`
      - `content_json = {"_tenon": {"noContent": true, "reason": "NO_DRAFT_AT_CUTOFF"}}`
  - Rescheduling safety:
    - Requeue path is rowcount-aware (`requeue_nonterminal_idempotent_job` returns `None` when no nonterminal row is updated).
    - Worker requires actual persisted requeue state when handler returns `_jobDisposition: "rescheduled"`; otherwise it retries/dead-letters to prevent RUNNING lock wedges.

## Testing

- `poetry run ruff check .` — PASS
- `poetry run pytest -q` — PASS (`999 passed`, coverage `99.05%`)

Typecheck note:
- No canonical typecheck command found in repo; `mypy` not installed in Poetry env, so typecheck was not run.

## How to manually verify

1. Schedule a candidate session and confirm day windows are created and day-close jobs are enqueued for Day 1/Day 5 text tasks.
2. During an open window, `PUT /api/tasks/{task_id}/draft` then `GET /api/tasks/{task_id}/draft`; confirm content and `updatedAt` persist.
3. Outside the window, call `PUT /api/tasks/{task_id}/draft`; confirm `409 TASK_WINDOW_CLOSED`.
4. After window end, run worker (or trigger the job) and confirm submission exists:
   - matches draft when draft exists, or
   - contains empty marker (`NO_DRAFT_AT_CUTOFF`) when no draft exists.
5. Re-run the same day-close job and confirm no duplicate/overwrite behavior (idempotent no-op when already submitted).

## Audit QA (manual runtime)

- **Overall verdict:** PASS
- **Execution method:** ASGI in-process harness (`httpx.AsyncClient(app=app, base_url="http://test")`)
- **Why not uvicorn:** sandbox bind blocked on `127.0.0.1:8010` (`operation not permitted`)
- **Evidence bundle paths:**
  - Folder: `.qa/issue201/manualqa_20260305T231220Z/`
  - Zip (original): `.qa/issue201/manualqa_20260305T231220Z.zip`
  - Zip (polish): `.qa/issue201/manualqa_20260305T231220Z_polish_20260305T233716Z.zip`
  - QA report: `.qa/issue201/manualqa_20260305T231220Z/QA_REPORT.md`

| Case | Result | Evidence |
|---|---|---|
| A | Draft round-trip (Day1 + Day5) + auth unowned session check | `.qa/issue201/manualqa_20260305T231220Z/responses/A_day1_get_draft.json`<br>`.qa/issue201/manualqa_20260305T231220Z/responses/A_day5_get_draft.json`<br>`.qa/issue201/manualqa_20260305T231220Z/responses/A_auth_unowned_session.json` |
| B | Draft persists across refresh | `.qa/issue201/manualqa_20260305T231220Z/responses/B_day1_get_refresh.json`<br>`.qa/issue201/manualqa_20260305T231220Z/responses/B_day5_get_refresh.json` |
| C | PUT outside window => `409 TASK_WINDOW_CLOSED` | `.qa/issue201/manualqa_20260305T231220Z/responses/C_put_outside_window.json` |
| D | Finalize from draft creates submission + draft finalized fields set | `.qa/issue201/manualqa_20260305T231220Z/db/D_finalize_from_draft.json` |
| E | No draft => empty marker submission created | `.qa/issue201/manualqa_20260305T231220Z/db/E_finalize_no_draft_marker.json` |
| F | Idempotency rerun => no duplicates/overwrite | `.qa/issue201/manualqa_20260305T231220Z/db/F_idempotency_rerun.json` |
| G | Manual submit precedence => finalizer no-op / no overwrite | `.qa/issue201/manualqa_20260305T231220Z/responses/G_manual_submit.json`<br>`.qa/issue201/manualqa_20260305T231220Z/responses/G_put_draft_after_submit.json`<br>`.qa/issue201/manualqa_20260305T231220Z/db/G_manual_submit_precedence.json` |
| H | Reschedule safety => no RUNNING wedge; lock transition captured | `.qa/issue201/manualqa_20260305T231220Z/db/H_job_reschedule_no_wedge.json`<br>`.qa/issue201/manualqa_20260305T231220Z/db/H_job_lock_transition.json` |

Additional evidence (polish artifacts):
- `.qa/issue201/manualqa_20260305T231220Z/responses/A_put_contract_shape.json`
- `.qa/issue201/manualqa_20260305T231220Z/responses/A_get_contract_shape.json`
- `.qa/issue201/manualqa_20260305T231220Z/db/A_upsert_uniqueness.json`
- `.qa/issue201/manualqa_20260305T231220Z/db/H_job_lock_transition.json`

Artifacts are redacted; no draft/submission bodies were logged.

## Risks / Rollout Notes

- `submissions.content_json` is internal storage for finalization/markers; it is not exposed as a submit request field.
- Day-close reschedule path includes wedge-proofing via rowcount-aware requeue + worker reschedule verification.
- Draft payload limits are enforced (`DRAFT_CONTENT_TOO_LARGE`), and draft write logs record sizes only (no draft content logging).
