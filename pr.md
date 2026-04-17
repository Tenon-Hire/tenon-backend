# Enforce Codespace-only Day 2/3 workflow and remove offline/local work permission #286

## 1. Summary
Winoe AI now enforces a Codespace-only Day 2/3 workflow end to end. Active Day 2 and Day 3 flows no longer expose legacy workspace fields, post-cutoff access is locked down with `TASK_WINDOW_CLOSED`, and cutoff evidence is recorded separately so evaluation stays anchored to the recorded cutoff SHA rather than mutable later workspace state.

## 2. Problem
The product requires canadidates to build from scratch in Codespaces, with the entire repo being their work. The backend still exposed legacy copy and response fields that suggested offline/local work was acceptable, and cutoff enforcement was not consistently applied across active Day 2/3 flows.

## 3. Root cause
- Contract issue: active Codespace init/status responses still exposed legacy fields that implied a pre-cutoff workspace basis.
- Enforcement issue: the backend did not uniformly block active Day 2/3 actions after cutoff across init, status, run, and submit.

## 4. Implementation summary
- Active Day 2/3 Codespace init/status responses now omit `baseTemplateSha` and `precommitSha`.
- Active Day 2/3 flows now call the shared cutoff gate before init, status, run, and submit.
- Day 2 and Day 3 cutoff evidence is written as separate `candidate_day_audits` rows.
- Day 2 submit persists `checkpointSha`.
- Day 3 submit persists `finalSha`.
- The response mapping and handler tests now reflect the cutoff contract directly.

## 5. API contract changes
- `baseTemplateSha` was removed from active Day 2/3 Codespace init/status responses.
- `precommitSha` was removed from active Day 2/3 Codespace init/status responses.
- Day 2 submit responses return `checkpointSha` for the Day 2 checkpoint.
- Day 3 submit responses return `finalSha` for the Day 3 final state.
- Post-cutoff error payloads include the cutoff basis fields needed for evaluation and audit traceability.

## 6. Cutoff enforcement behavior
- Active Day 2/3 `codespace/init`, `codespace/status`, `run`, and `submit` requests now reject after cutoff with `409 TASK_WINDOW_CLOSED`.
- Rejection payloads include cutoff details such as `cutoffCommitSha`, `cutoffAt`, and `evalBasisRef`.
- The same cutoff gate is used consistently across the active Day 2/3 backend paths, so post-cutoff behavior is uniform instead of route-specific.

## 7. Evaluation basis behavior
- The evaluation basis is pinned to the recorded cutoff SHA after cutoff, even if `workspace.latest_commit_sha` changes later.
- Successful pre-cutoff Day 2/Day 3 submit responses may still return `cutoffCommitSha = null` and `evalBasisRef = null` because the cutoff audit row does not exist yet at that moment.
- Once the cutoff audit exists, later active requests resolve cutoff details from the audit row rather than from mutable workspace state.

## 8. Persistence / model impact
- `candidate_day_audits` now carries the authoritative Day 2 and Day 3 cutoff record.
- Separate audit rows are persisted for `dayIndex = 2` and `dayIndex = 3`.
- The recorded cutoff SHA and evaluation basis reference are stored per day, which keeps Day 2 and Day 3 evaluation inputs distinct.

## 9. Tests added / updated
- `tests/candidates/routes/test_candidates_submissions_router_init_codespace_success_path_routes.py`
- `tests/candidates/routes/test_candidates_schedule_gates_run_and_submit_post_cutoff_return_task_window_closed_routes.py`
- `tests/tasks/routes/test_tasks_run_codespace_init_rejects_after_day_audit_routes.py`
- `tests/tasks/routes/test_tasks_run_submit_rejects_after_day_audit_routes.py`
- `tests/tasks/routes/test_tasks_run_codespace_status_returns_summary_routes.py`
- `tests/tasks/routes/test_tasks_run_codespace_status_naive_cutoff_routes.py`
- `tests/tasks/routes/test_tasks_submit_submit_day3_debug_returns_and_persists_final_sha_routes.py`
- `tests/candidates/routes/test_candidates_session_api_current_task_includes_cutoff_fields_when_day_audit_exists_routes.py`
- `tests/candidates/routes/test_candidates_session_api_current_task_returns_null_cutoff_fields_when_day_audit_missing_routes.py`
- `tests/tasks/routes/test_tasks_run_codespace_init_works_for_debug_task_routes.py`

## 10. Manual QA evidence
- Command: `poetry run pytest -o addopts='' tests/candidates/routes/test_candidates_submissions_router_init_codespace_success_path_routes.py tests/candidates/routes/test_candidates_schedule_gates_run_and_submit_post_cutoff_return_task_window_closed_routes.py tests/tasks/routes/test_tasks_submit_submit_day3_debug_returns_and_persists_final_sha_routes.py tests/tasks/routes/test_tasks_run_codespace_init_rejects_after_day_audit_routes.py tests/tasks/routes/test_tasks_run_submit_rejects_after_day_audit_routes.py tests/tasks/routes/test_tasks_run_codespace_status_returns_summary_routes.py tests/tasks/routes/test_tasks_run_codespace_status_naive_cutoff_routes.py`
- Result: `7 passed`
- Command: `poetry run pytest`
- Result: `1711 passed`, coverage `96.15%`
- Day 2 init success response did not include legacy bundle fields.
- Day 2 status before cutoff returned normal status with `cutoffCommitSha = null` and `cutoffAt = null`.
- Day 2 submit returned `checkpointSha` and null cutoff fields before cutoff.
- Day 2 post-cutoff `status`, `run`, and `submit` rejected with `409 TASK_WINDOW_CLOSED` and cutoff details.
- Day 3 submit returned `finalSha`.
- Day 3 post-cutoff `status` rejected with `409 TASK_WINDOW_CLOSED` and cutoff details.
- Separate Day 2 and Day 3 audit rows existed in the database with different `dayIndex` values and different cutoff SHAs.
- Mutating `workspace.latest_commit_sha` after cutoff did not change the cutoff details returned by later active requests.
- Focused tests passed.
- Full repo test suite passed.

## 11. Risks / follow-ups
- Frontend copy and UI should stay aligned with the tightened backend cutoff contract so candidates do not see outdated offline/local wording.

## 12. Fixes #286
