# Title

- "P0 Candidate Core: Lock simulation content until schedule begins (Issue #199)"

## TL;DR

- Added a centralized schedule-start gate for candidate content retrieval, returning a stable `SCHEDULE_NOT_STARTED` contract before Day 1 begins.
- Gated candidate content surfaces that can leak scenario IP (`current_task`, codespace status, codespace init) until `windowStartAt`.
- Updated resolve behavior to keep pre-start responses `200` but minimal, with timing fields for locked-state UI and no storyline/task/repo/codespace payload leakage.
- Preserved auth/ownership precedence so invalid ownership still returns ownership/auth errors first (not schedule-gate errors).
- Added integration/unit coverage to lock in the pre-start behavior and contract.

## What changed

- Central schedule gate helper:
  - Added `app/services/candidate_sessions/schedule_gates.py` with:
    - `compute_day1_window(candidate_session)`
    - `build_schedule_not_started_error(...)`
    - `is_schedule_started_for_content(...)`
    - `ensure_schedule_started_for_content(...)`
  - `build_schedule_not_started_error` returns `409` + `SCHEDULE_NOT_STARTED` with `startAt`, `windowStartAt`, `windowEndAt`.
  - Added `SCHEDULE_NOT_STARTED` constant in `app/core/errors.py`.
  - Re-exported via `app/services/candidate_sessions/__init__.py` and compat shim `app/domains/candidate_sessions/service/schedule_gates.py`.
- Gated candidate content endpoints:
  - `GET current_task`: `app/api/routers/candidate_sessions_routes/current_task_logic.py`
    - `build_current_task_view(...)` now calls `cs_service.ensure_schedule_started_for_content(cs, now=now)`.
  - `GET codespace/status`: `app/api/routers/tasks/status.py`
    - `codespace_status_route(...)` now enforces `ensure_schedule_started_for_content`.
  - `POST codespace/init`: `app/api/routers/tasks/init.py`
    - `init_codespace_route(...)` now enforces `ensure_schedule_started_for_content`.
- Resolve route behavior (`app/api/routers/candidate_sessions_routes/responses.py`):
  - Pre-start resolve still returns `200`.
  - Added locked-state timing fields on resolve payload:
    - `startAt`
    - `windowStartAt`
    - `windowEndAt`
  - Resolve stays minimal pre-start (no storyline/task/repo/codespace content sections).
  - Schema updated in `app/schemas/candidate_sessions.py` to include these timing fields.

## API contract

- Pre-start content requests return:
  - HTTP status: `409`
  - `errorCode`: `SCHEDULE_NOT_STARTED`
  - `retryable`: `true`
  - `details.startAt`, `details.windowStartAt`, `details.windowEndAt`

```json
{
  "detail": "Simulation has not started yet.",
  "errorCode": "SCHEDULE_NOT_STARTED",
  "retryable": true,
  "details": {
    "startAt": "2026-03-10T13:00:00Z",
    "windowStartAt": "2026-03-10T13:00:00Z",
    "windowEndAt": "2026-03-10T21:00:00Z"
  }
}
```

- Resolve additions for locked UI:
  - `startAt`, `windowStartAt`, `windowEndAt` are included on resolve response pre-start so frontend can render "starts at" locked state without content leakage.

## Tests / Verification

- Commands run:
  - `poetry run ruff check .` -> PASS
  - `poetry run ruff format --check .` -> PASS (`761 files already formatted`)
  - `poetry run pytest` -> PASS (`936 passed in 16.97s`)
- Key tests added/updated:
  - Current task blocks pre-start:
    - `tests/api/test_candidate_session_resolve.py`
      - `test_current_task_pre_start_returns_schedule_not_started`
  - Codespace endpoints block pre-start:
    - `tests/api/test_candidate_schedule_gates.py`
      - `test_codespace_status_pre_start_returns_schedule_not_started`
    - `app/api/routers/tasks/init.py` now uses the same gate path (`ensure_schedule_started_for_content`) as status; regression tests updated to explicitly unlock schedules where init is expected to succeed:
      - `tests/api/test_task_run.py`
      - `tests/api/test_task_submit.py`
  - Resolve pre-start is minimal/no-leak:
    - `tests/api/test_candidate_schedule_gates.py`
      - `test_resolve_pre_start_returns_locked_payload_without_content_leaks`
  - Ownership precedence preserved:
    - `tests/api/test_candidate_schedule_gates.py`
      - `test_current_task_mismatch_still_ownership_error_before_schedule_gate`

## Manual QA (runtime / ASGI harness)

- Overall verdict: PASS (A-F)
- Preferred uvicorn bind attempt failed in this environment with `operation not permitted` when binding to `127.0.0.1:8010`.
- QA therefore executed via an in-process ASGI harness.
- Command run:
  - `TENON_ENV=test poetry run python .qa/issue199/issue199_20260305_062941/manual_http_harness.py`
- Evidence bundle path:
  - `.qa/issue199/issue199_20260305_062941/`
- Artifacts:
  - `QA_REPORT.md`
  - `env.txt`
  - `commands.log`
  - `manual_http_harness.py`
  - `manual_harness_output.txt`
  - `qa_summary.json`
  - `responses/*.json` (A-F response captures)

| Check | Expected | Actual | Evidence |
| --- | --- | --- | --- |
| A) Resolve pre-start | `200` + timing fields (`startAt`, `windowStartAt`, `windowEndAt`) + no leak keys/URLs | PASS | `responses/A_resolve_prestart.json` |
| B) `current_task` pre-start | `409` `SCHEDULE_NOT_STARTED` with details `{startAt, windowStartAt, windowEndAt}` | PASS | `responses/B_current_task_prestart.json` |
| C) `codespace/status` pre-start | `409` `SCHEDULE_NOT_STARTED` with details | PASS | `responses/C_codespace_status_prestart.json` |
| D) `codespace/init` pre-start | `409` `SCHEDULE_NOT_STARTED` with details | PASS | `responses/D_codespace_init_prestart.json` |
| E) Ownership precedence | Ownership/auth error wins (not schedule gate) | PASS (`403 CANDIDATE_INVITE_EMAIL_MISMATCH`) | `responses/E_ownership_precedence.json` |
| F) Post-start unlock | `current_task` `200` with description; codespace endpoints not schedule-gated | PASS | `responses/F1_current_task_poststart.json`, `responses/F2_codespace_status_poststart.json`, `responses/F3_codespace_init_poststart.json` |

- GitHub client was stubbed in the harness to validate schedule-gate behavior independently of external integrations.
- `.qa/` is gitignored and artifacts are not committed; if sharing is needed, zip and distribute externally.

## Content-surface audit (anti-leak proof)

- Commands run:
  - `rg -n "codespace_url|codespaceUrl|repoUrl|templateRepo|github.com" app/api app/services app/domains`
  - `rg -n "TaskPublic|description|resources|storyline|prestart" app/api app/services app/domains`
  - `rg -n "APIRouter\\(|/api/tasks|/tasks/" app/api/routers`
- Findings summary:
  - Candidate-accessible leak surfaces are only:
    - `GET /api/candidate/session/{candidate_session_id}/current_task` (`TaskPublic.description` via `build_current_task_response`)
    - `GET /api/tasks/{task_id}/codespace/status` (`repoUrl`, `codespaceUrl`)
    - `POST /api/tasks/{task_id}/codespace/init` (`repoUrl`, `codespaceUrl`)
  - All of the above are now schedule-gated before content is returned.
  - Recruiter-only surfaces containing richer task/repo fields (for example simulation detail and submissions views) remain recruiter-auth protected and unchanged.

## Risks / Rollout notes

- Unlock behavior is tied to Day 1 `windowStartAt`; window-end/read-only enforcement is intentionally handled in a separate issue.
- Frontend should use `retryable: true` + `details.windowStartAt` for near-start polling/retry UX.
- `mypy` is not installed in this local environment (`poetry run mypy --version` -> `Command not found: mypy`), so no mypy run is included.

## Demo checklist

1. Schedule a candidate session in the future.
2. Call `GET /api/candidate/session/{candidate_session_id}/current_task` and `GET /api/tasks/{task_id}/codespace/status` before `windowStartAt` and confirm `409 SCHEDULE_NOT_STARTED`.
3. Resolve pre-start via `GET /api/candidate/session/{token}` and confirm timing fields are present with no storyline/task/repo/codespace content leakage.
4. Move time past `windowStartAt` and confirm content endpoints return normal payloads.
