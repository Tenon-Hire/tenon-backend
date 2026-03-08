# PR Title
Issue #204: P0 Integrity - Day 2/Day 3 cutoff enforcement with immutable evaluation basis

## TL;DR

- Implements cutoff enforcement for Day 2/Day 3 coding tasks.
- Evaluation basis is now pinned to immutable stored cutoff evidence, not mutable repo HEAD at reviewer read time.
- Adds internal `day_close_enforcement` jobs at window end to revoke write access, capture cutoff branch HEAD SHA, and persist write-once cutoff audit records.
- Candidate/recruiter submission surfaces now include `cutoffCommitSha` and `cutoffAt`; when cutoff exists, `commitSha` resolves to the stored cutoff SHA.
- Iteration 2 fail-closed correction is included: missing candidate GitHub identity now fails/retries and does not persist cutoff audit.

## Problem / Why This Change

MVP integrity requires timeboxed evaluation evidence for coding days. Without cutoff enforcement, review could drift to mutable repository HEAD after window close. This change ensures:

- Day-close enforcement removes candidate write capability at window end.
- Evaluation uses an immutable stored cutoff SHA/ref.
- Post-cutoff write-bearing actions remain blocked with `TASK_WINDOW_CLOSED`.

## What Changed

- Added write-once day-audit persistence for cutoff evidence per coding day.
- Added scheduling and worker handling for `day_close_enforcement` jobs.
- Added GitHub revocation + cutoff SHA capture flow in day-close handler.
- Updated candidate submit and recruiter evidence responses to surface cutoff basis and pin `commitSha` when cutoff exists.
- Preserved post-cutoff endpoint behavior (`TASK_WINDOW_CLOSED`) for write-bearing code-day actions.

## Data Model / Schema Changes

Chosen model: Option B (`candidate_day_audits`).

- Table: `candidate_day_audits`
- Keying: unique `(candidate_session_id, day_index)`
- Day constraint: `day_index IN (2, 3)`
- Immutable cutoff evidence columns:
  - `cutoff_at`
  - `cutoff_commit_sha`
  - `eval_basis_ref`
- Write-once semantics are enforced by creation-only repository flow (`create_day_audit_once`) plus DB uniqueness, so reruns return existing audit and do not overwrite evidence.
- Supporting field: `candidate_sessions.github_username` added for collaborator revocation targeting.

## API / Contract Changes

- Candidate submit responses now include cutoff basis fields:
  - `cutoffCommitSha`
  - `cutoffAt`
  - `evalBasisRef`
- Recruiter submission list/detail responses now include cutoff basis fields:
  - `cutoffCommitSha`
  - `cutoffAt`
  - `evalBasisRef`
- Commit basis pinning:
  - If cutoff evidence exists, `commitSha` is set to stored `cutoffCommitSha`.
  - If cutoff evidence does not exist, `commitSha` remains submission commit SHA behavior.
- Post-cutoff write-bearing run/submit behavior remains `TASK_WINDOW_CLOSED`.

## Worker / Job Behavior

New internal job type: `day_close_enforcement`.

- Scheduled at task window end for Day 2/Day 3 coding tasks.
- Handler flow:
  1. Resolve candidate session/task/workspace.
  2. Revoke candidate repo write access (remove collaborator).
  3. Resolve evaluation branch (workspace default or repo default).
  4. Capture branch HEAD SHA at job execution time.
  5. Persist `cutoff_at`, `cutoff_commit_sha`, `eval_basis_ref` as write-once evidence.
- Idempotency:
  - Repeated runs return existing cutoff evidence and do not overwrite it.
  - Collaborator already absent (`404`) is treated as idempotent success for revocation.
- Fail-closed correction (Iteration 2):
  - If candidate GitHub identity is missing, handler raises and job retries (no warn-and-continue).
  - No cutoff audit is persisted in that failure path.

## Security / Integrity Invariants

- Evaluation basis is immutable once cutoff evidence exists.
- No client-provided SHA is trusted for cutoff basis; server captures from GitHub branch HEAD.
- Day-close enforcement does not auto re-grant write access.
- Recruiter/candidate evidence views consistently report stored cutoff basis.

## Testing

Commands and results from implementation verification:

- `poetry run pytest --no-cov tests/unit/test_day_close_enforcement_handler.py tests/unit/test_submit_task_handler.py` -> PASS (`16 passed`)
- `poetry run ruff check .` -> PASS
- `poetry run pytest` -> PASS (`1059 passed`)

Coverage highlights relevant to this issue:

- Day-close enforcement handler tests:
  - cutoff persistence + revocation
  - idempotent no-overwrite reruns
  - transient GitHub retry behavior
  - fail-closed missing GitHub identity (retry + no audit write)
  - collaborator-already-absent idempotency path
- Day-audit repository tests:
  - create-once semantics
  - uniqueness/race paths returning existing evidence
- Recruiter submission API tests:
  - list/detail include cutoff evidence and pinned commit basis
- Candidate schedule gate tests:
  - post-cutoff run/submit return `TASK_WINDOW_CLOSED`

## Audit QA (manual / runtime)

Overall verdict: `PASS`. Issue #204 is PR-ready from a manual/runtime QA perspective.

Runtime method used:

- Attempted real localhost startup first with `poetry run uvicorn app.main:app --host 127.0.0.1 --port 8012`.
- Startup failed in sandbox with bind error: `[Errno 1] operation not permitted`.
- QA then used an ASGI in-process fallback with an isolated SQLite QA DB, real FastAPI routes/services/repos/worker flow, and GitHub edge stubs only.

Evidence bundle paths:

- `.qa/issue204/manual_qa_20260308_191737/`
- `.qa/issue204/manual_qa_20260308_191737.zip`

Key evidence files:

- `.qa/issue204/manual_qa_20260308_191737/QA_REPORT.md`
- `.qa/issue204/manual_qa_20260308_191737/artifacts/scenario_results.json`
- `.qa/issue204/manual_qa_20260308_191737/logs/uvicorn_bind_failure.log`
- `.qa/issue204/manual_qa_20260308_191737/db/snapshot_jobs_all.json`
- `.qa/issue204/manual_qa_20260308_191737/db/snapshot_candidate_day_audits_all.json`
- `.qa/issue204/manual_qa_20260308_191737/db/snapshot_submissions_all.json`
- `.qa/issue204/manual_qa_20260308_191737/logs/secret_scan.log`
- `.qa/issue204/manual_qa_20260308_191737/scripts/manual_qa_issue204.py`

Scenario matrix:

| Scenario | Result | Finding |
| --- | --- | --- |
| A | PASS | day-close scheduling created `day_close_enforcement` jobs for Day 2/3 |
| B | PASS | successful enforcement persisted immutable cutoff evidence; revoke attempted before branch fetch |
| C | PASS | rerun idempotent; cutoff evidence unchanged |
| D | PASS | collaborator `404` treated as idempotent success; audit persisted |
| E | PASS | missing `github_username` failed closed; job rescheduled; no audit row written |
| F | PASS | recruiter list/detail surfaces pinned cutoff basis; `commitSha` resolves to cutoff SHA |
| G | PASS | candidate submit response pins `commitSha == cutoffCommitSha`; mutable submission SHA does not win after cutoff |
| H | PASS | post-cutoff run/submit returned `TASK_WINDOW_CLOSED`; no mutation side effects |

Commands run + results:

- `poetry run uvicorn app.main:app --host 127.0.0.1 --port 8012` -> FAIL-EXPECTED (sandbox bind denied)
- `poetry run python .qa/issue204/manual_qa_20260308_191737/scripts/manual_qa_issue204.py --bundle-dir .qa/issue204/manual_qa_20260308_191737` -> PASS
- secret scan over bundle -> PASS (`NO_MATCHES`)
- zip bundle command -> PASS

Notes / limitations:

- localhost bind was disallowed in sandbox, so loopback HTTP runtime could not be used
- GitHub/Actions were stubbed only at integration boundaries
- auth dependencies were overridden in the harness to exercise protected routes with real app internals

Final conclusion: manual/runtime QA passed, no blocker was found, and issue #204 is ready for PR raise.

## Risks / Rollout Notes

- Cutoff SHA is captured from branch HEAD at job execution time after revocation; delayed worker execution delays snapshot timing.
- Missing GitHub identity now fails/retries and can dead-letter until identity data is remediated.
- Optional branch protection hardening (force-push restrictions, stricter branch policy) is not included in this issue.
- Repo-wide `black --check .` still has pre-existing formatting debt outside this issue scope; touched files/tests are clean and full suite passes.

## Demo / Reviewer Checklist

- Create and schedule a candidate session.
- Progress candidate to Day 2 or Day 3 and reach cutoff.
- Confirm `day_close_enforcement` job runs.
- Confirm candidate write access to repo is revoked.
- Confirm candidate/recruiter submission responses show stored cutoff basis (`commitSha`, `cutoffCommitSha`, `cutoffAt`).
- Confirm post-cutoff run/submit actions return `TASK_WINDOW_CLOSED`.
- Confirm rerunning enforcement does not overwrite existing cutoff evidence.
