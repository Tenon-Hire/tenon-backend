# Enable candidate invite flow from active Trial through email, empty repo, and Codespace provisioning #283
Closes #283.

## Summary
- The Talent Partner invite flow now works end to end from an `active_inviting` Trial through invite creation, unique invite URL generation, invite email send, candidate claim, empty repo bootstrap, and GitHub Codespace provisioning.
- Candidate repos are now created as empty repos under `winoe-ai-repos/winoe-ws-{session_id}` and bootstrapped with only `.devcontainer/devcontainer.json`, `.github/workflows/evidence-capture.yml`, `.gitignore`, and `README.md`.
- No template cloning happens and no precommit is applied. Fresh live QA for candidate session `28` proved `template_repo_full_name=null`, `precommit_sha=null`, and `precommit_details_json=null`.
- Codespace init/status now refreshes the live GitHub Codespace state and persists the normalized lower-case state back to the workspace row, which closed the stale-state gap seen during local QA.
- The invite response includes the unique `inviteUrl` contract used by the Talent Partner UI copy action, and candidate claim was validated through the supported local dev email-verification bypass path.

## Files changed
- `app/integrations/github/client/integrations_github_client_github_client_repos_client.py`: hardens empty-repo creation identity checks and changes `get_codespace()` to use the user-scoped Codespaces lookup with repo validation.
- `app/submissions/repositories/github_native/workspaces/submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_mutations_repository.py`: adds persisted workspace `codespace_state` writes.
- `app/submissions/services/submissions_services_submissions_workspace_bootstrap_service.py`: replaces template/bootstrap assumptions with the empty-repo bootstrap path, writes only the required bootstrap files, creates the Codespace, and stores normalized Codespace metadata.
- `app/submissions/services/submissions_services_submissions_workspace_repo_state_service.py`: refreshes live Codespace state from GitHub and persists normalized lower-case state into the workspace row.
- `app/submissions/services/use_cases/submissions_services_use_cases_submissions_use_cases_codespace_init_service.py`: triggers empty-repo workspace provisioning and post-init Codespace refresh during candidate init.
- `app/submissions/services/use_cases/submissions_services_use_cases_submissions_use_cases_codespace_status_service.py`: refreshes persisted Codespace state during status reads.
- `app/tasks/routes/tasks/tasks_routes_tasks_tasks_codespace_status_routes.py`: returns the refreshed persisted Codespace state through the candidate status route.
- `scripts/local_qa_backend.sh`: committed local QA wrapper that pins the supported local bypass flags before delegating to `runBackend.sh`.
- `README.md`: documents `bash scripts/local_qa_backend.sh` as the local QA backend entrypoint for invite/claim verification.
- `tests/integrations/github/client/test_integrations_github_client_github_client_misc_methods_client.py`: covers the `/user/codespaces/{name}` lookup path.
- `tests/scripts/test_local_qa_backend_shell.py`: covers the local QA wrapper env pinning and `.env` reload protection.

## Why
- The Talent Partner invite flow needed to work end to end from Trial invite through candidate claim.
- The v4 pivot required from-scratch repo bootstrap instead of template cloning and precommit application.
- Codespace state persistence had a stale-state gap; live refresh and DB persistence were needed so status reads reflected the actual GitHub Codespace state.
- Local QA needed a deterministic committed path for claim-bypass validation.

## Implementation details
- `get_codespace()` now calls `GET /user/codespaces/{name}` and verifies that the returned `repository.full_name` matches the expected repo before accepting the payload.
- The Codespace refresh path now normalizes GitHub state to lower case and persists it into the workspace row through `set_codespace_state(...)`.
- Codespace refresh is triggered during both Codespace init and Codespace status flows, so the DB is repaired from live GitHub state on those paths.
- The empty-repo bootstrap path creates the candidate repo under `winoe-ai-repos`, writes only `.devcontainer/devcontainer.json`, `.github/workflows/evidence-capture.yml`, `.gitignore`, and `README.md`, then stores the normalized Codespace name/state/url returned by GitHub.
- Template and precommit fields remain unset on this path, which matches the v4 requirement that the repo stay empty apart from config and the project brief.
- `scripts/local_qa_backend.sh` now loads env once, forces `DEV_AUTH_BYPASS=1`, forces `WINOE_DEV_AUTH_BYPASS=1`, and redirects `ENV_FILE=/dev/null` before calling `runBackend.sh` so `.env` defaults do not reset the local QA flags.

## QA
### Automated validation
- Focused `pytest` slices were run with `--no-cov` against the GitHub client, workspace bootstrap/state persistence, Codespace init/status, and local QA shell wrapper coverage.
- `poetry run ruff check .`
- `git diff --check`
- `bash ./precommit.sh`
- Final result: `precommit` passed.

### Fresh live QA
- Trial id: `20`
- Candidate session id: `28`
- Candidate email: `qa283live9.1776355353@gmail.com`
- Invite response payload:

```json
{"candidateSessionId":28,"token":"2dyizjDp3uG4_Cpx3zEU-tXQ4kJ0roScw0_veFOhqwU","inviteUrl":"http://localhost:3000/candidate/session/2dyizjDp3uG4_Cpx3zEU-tXQ4kJ0roScw0_veFOhqwU","outcome":"created"}
```

- Invite URL: `http://localhost:3000/candidate/session/2dyizjDp3uG4_Cpx3zEU-tXQ4kJ0roScw0_veFOhqwU`
- The invite response returned the unique `inviteUrl` used by the Talent Partner UI copy action.
- Email DB evidence:

```text
invite_email_status=sent
invite_email_error=null
invite_email_last_attempt_at=2026-04-16T16:02:33.682493+00:00
invite_email_sent_at=2026-04-16T16:02:33.682493+00:00
```

- Repo full name: `winoe-ai-repos/winoe-ws-28`
- Exact repo contents:

```text
.devcontainer/devcontainer.json
.github/workflows/evidence-capture.yml
.gitignore
README.md
```

- Template/precommit DB proof:

```text
template_repo_full_name=null
precommit_sha=null
precommit_details_json=null
```

- Codespace name: `symmetrical-couscous-4j9qqw4qwjqvf69r`
- Codespace URL: `https://symmetrical-couscous-4j9qqw4qwjqvf69r.github.dev`
- GitHub codespace state: `Available`
- DB workspace row state: `available`
- Refresh route used: `GET /api/tasks/97/codespace/status` with `Authorization: Bearer candidate:qa283live9.1776355353@gmail.com` and `x-candidate-session-id: 28`
- Claim request: `POST /api/candidate/session/2dyizjDp3uG4_Cpx3zEU-tXQ4kJ0roScw0_veFOhqwU/claim` with `Authorization: Bearer candidate:qa283live9.1776355353@gmail.com`
- Claim response proof: candidate session returned `status=in_progress`
- Candidate session DB row after claim:

```text
status=in_progress
claimed_at=2026-04-16T16:03:32.393842+00:00
started_at=2026-04-16T16:03:32.393842+00:00
candidate_auth0_sub=candidate:qa283live9.1776355353@gmail.com
candidate_auth0_email=qa283live9.1776355353@gmail.com
candidate_email=qa283live9.1776355353@gmail.com
candidate_timezone=America/New_York
scheduled_start_at=2026-04-15T15:48:00+00:00
schedule_locked_at=2026-04-16T16:03:53.462718+00:00
```

### Acceptance criteria checklist
- [x] Talent Partner invites by full name and email from `active_inviting` Trial
- [x] Unique invite URL generated and emailed
- [x] Copyable invite link in Talent Partner UI
- [x] Empty candidate repo created under the Winoe repos org
- [x] Repo initialized with `.devcontainer/devcontainer.json`, `README.md`, `.gitignore`, and evidence-capture workflow
- [x] No template cloning, no precommit application
- [x] GitHub Codespace provisioned for the repo
- [x] Candidate can claim invite via local dev email verification bypass

## QA nuances
- The persisted Codespace-state refresh proof was validated through the day-2 Codespace status route in local QA.
- The local claim proof uses the supported local-only bypass path through the committed `scripts/local_qa_backend.sh`.
- These are QA/runtime notes, not product-facing behavior changes.

## Conclusion
Issue #283 is addressed. Fresh live QA satisfied the acceptance criteria above, and this PR is ready to raise.
