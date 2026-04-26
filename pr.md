# 1. Title

Unblock real Day 2 candidate verification by fixing GitHub/Codespace reliability, repo activation, and Actions dispatch behavior

# 2. Linked / Related Issues

- Winoe-AI/winoe-backend issue #285: Require GitHub username capture and fix Codespace init contract
- Winoe-AI/winoe-backend issue #286: Enforce Codespace-only Day 2/3 workflow and remove offline/local work permission
- Related frontend dependency: Winoe-AI/winoe-frontend issue #183

# 3. Problem / Why

Day 2 could not be verified end to end on the real stack until the backend-side Codespace and Actions contract was made reliable.

The original blockers were the ones tracked in #285 and #286:

- GitHub username capture and Codespace init contract support were incomplete.
- The workflow still had ambiguity around Codespace-only candidate work.
- The backend needed to produce the right day-flow state so the frontend could open, poll, and close Day 2 correctly.

During live QA, additional reliability issues surfaced that had to be fixed before real candidate flow could be trusted:

- shared-time consistency and candidate-session day-flow correctness
- workspace repo / Codespace bootstrap robustness
- archived workspace repos causing `workflow_dispatch` runs to queue without jobs
- repo activation before Codespace init
- repo activation before GitHub Actions dispatch

# 4. What Changed

- Backend support now matches the GitHub username / Codespace init contract expected by the candidate flow.
- Codespace-only workflow enforcement is supported from the backend side.
- Candidate-session day-flow and shared-time handling were tightened so the frontend receives stable open/closed behavior.
- Workspace repo and Codespace bootstrap state handling was hardened.
- Workspace repos are activated / unarchived before Codespace init.
- Workspace repos are activated / unarchived before GitHub Actions run dispatch.
- The run-tests path now avoids the failure mode where a `workflow_dispatch` stays queued with `jobs: []`.
- Targeted backend tests were added or updated around repo activation and run-tests behavior.

# 5. Key Files Changed

- `app/integrations/github/client/integrations_github_client_github_client_repos_client.py`
- `app/submissions/services/submissions_services_submissions_workspace_bootstrap_service.py`
- `app/submissions/services/submissions_services_submissions_workspace_repo_state_service.py`
- `app/submissions/services/use_cases/submissions_services_use_cases_submissions_use_cases_run_tests_service.py`
- Targeted backend tests covering repo activation, Codespace init, and run dispatch behavior

# 6. QA / Validation Summary

Validation was done in two layers:

- Targeted backend checks passed for repo activation and run-tests behavior.
- Ruff checks passed for the touched backend surface.
- Full-stack live QA later exercised the real frontend + backend stack with a real browser auth session and no QA-driver state seeding.

The backend changes were verified by observing the real candidate flow from open Day 2 through run-tests completion and submit completion on the live stack.

# 7. Live Evidence Summary

- A live GitHub Actions run on `winoe-ai-repos/winoe-ws-36` was observed stuck in `queued` with `jobs: []`, which confirmed the archived-repo / activation failure mode.
- After repo activation, a later Actions run succeeded, confirming the backend fix for dispatch reliability.
- The final contract-live QA on the real stack reached terminal run-tests success and a successful submit on the candidate flow.
- The frontend open-day and closed-day artifacts show the backend-backed open/closed day behavior that the UI now consumes.

# 8. Risks / Follow-Ups

- This backend PR unblocked real Day 2 Actions dispatch and verification, but it does not by itself close the frontend issue.
- If GitHub template repo state changes again, repo activation / unarchive preflight should continue to run before init and dispatch.
- Any future Codespace or Actions contract changes should be revalidated against the live candidate flow, not just unit tests.

# 9. Reviewer Notes

- The important outcome here is reliability: real Day 2 candidate execution can now be verified on the live stack.
- This work is the backend side of the broader Day 2 fix; the frontend PR #183 is still the UI-facing part of the overall flow.
- The root causes were not just one endpoint. They were a combination of contract mismatch, repo state handling, and Actions dispatch robustness.
- The queued-with-no-jobs failure mode is the key evidence that repo activation had to happen before dispatch.

Worker Report:

- Summary
  - Updated `pr.md` only to describe the backend reliability work that unblocked real Day 2 verification.
- Files changed
  - `pr.md`
- Commands run
  - `sed -n '1,260p' pr.md` - pass
  - `rg -n "queued|jobs: \[\]|activation|unarchive|workflow_dispatch|repo|Codespace|github username|pollAfterMs|run_tests|Submit" ...` - pass
- Risks / assumptions
  - Assumed the live QA findings are the final source of truth for backend root causes and validation wording.
  - Kept the backend PR honest about scope: it unblocked verification, but it does not alone close the frontend issue.
- Open questions / blockers
  - None
