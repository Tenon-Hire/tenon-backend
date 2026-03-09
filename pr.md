# Title
Issue #138 backend contract: expose cutoff evaluation fields on candidate runtime endpoints

## TL;DR
- Added cutoff evaluation fields to candidate current-task responses and candidate codespace status responses.
- Candidate current-task flow now reads day-audit cutoff data and includes it in `TaskPublic`.
- Candidate codespace/workspace status now reads day-audit cutoff data and returns it in `CodespaceStatusResponse`.
- Cutoff datetime handling normalizes naive datetimes to UTC-aware values before response serialization.
- Recruiter behavior remains unchanged.

## Problem / Context
Candidate runtime endpoints were not exposing cutoff evaluation fields, while recruiter submissions already had them. Because of this contract gap, candidate post-cutoff UI could not reliably activate in live runtime even when cutoff had been enforced.

## What Changed
- `TaskPublic` now includes:
  - `cutoffCommitSha`
  - `cutoffAt`
- Candidate current-task logic now loads day audit for the current task day and threads it into response construction.
- Current-task response builder now resolves cutoff fields from day audit and normalizes naive cutoff datetimes to UTC.
- `CodespaceStatusResponse` now includes:
  - `cutoffCommitSha`
  - `cutoffAt`
- Candidate codespace/workspace status route now fetches day audit for candidate session + task day and returns cutoff fields.

## Files Touched
- `app/api/routers/candidate_sessions_routes/current_task_logic.py`
- `app/api/routers/candidate_sessions_routes/responses.py`
- `app/api/routers/tasks/status.py`
- `app/schemas/tasks.py`
- `app/schemas/submissions.py`
- `tests/api/test_candidate_session_api.py`
- `tests/api/test_task_run.py`

## API Contract Summary
Candidate runtime surfaces now expose cutoff evaluation fields:
- Candidate current-task response (`TaskPublic`) includes `cutoffCommitSha` and `cutoffAt`.
- Candidate codespace/workspace status response (`CodespaceStatusResponse`) includes `cutoffCommitSha` and `cutoffAt`.

Null behavior:
- When no day audit exists for the candidate session + day, both fields return `null`.

## Testing
- Command:
  - `poetry run pytest tests/api/test_candidate_session_api.py tests/api/test_task_run.py --cov-fail-under=0`
- Result:
  - PASS (`42 passed`)

New/updated coverage verifies:
- current-task includes cutoff fields when day audit exists
- current-task returns null cutoff fields when day audit is absent
- codespace status includes cutoff fields when day audit exists
- codespace status returns null cutoff fields when day audit is absent

## Integration Note
This backend contract patch unblocks frontend issue #138 candidate post-cutoff runtime behavior by providing authoritative cutoff evaluation fields on candidate endpoints.

## Risks / Rollout Notes
- Change is additive and contract-safe: new fields are optional/null-safe.
- Recruiter-side behavior is unchanged.
- Cutoff values continue to come from day-audit as source of truth.
