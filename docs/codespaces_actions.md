# Codespaces + GitHub Actions Flow

Winoe now runs code tasks entirely from an empty candidate repo, Codespaces for editing, and Actions for tests.

## Candidate flow (backend endpoints)
0) `POST /api/trials/{trialId}/invite`
   - Creates an empty Trial workspace repo with devcontainer, brief, and evidence workflow.
1) `POST /api/tasks/{taskId}/codespace/init`
   - Creates or resolves the candidate repo; invites candidate via GitHub username.
   - Returns repo URL + Codespaces URL, default branch, workspace id, and stores the repo head SHA.
2) `POST /api/tasks/{taskId}/run`
   - Triggers `workflow_dispatch` on the workspace repo with optional `workflowInputs` + `branch`.
   - Polls the dispatched run and parses artifacts; returns `{status, passed, failed, total, stdout, stderr, runId, workflowUrl, commitSha}`.
3) `GET /api/tasks/{taskId}/run/{runId}`
   - Fetches an existing run result (polling helper) and returns the same normalized payload.
4) `POST /api/tasks/{taskId}/submit`
   - Triggers run (if needed) and stores commit/workflow ids, test output, and evidence summary from the candidate repo.
5) `GET /api/tasks/{taskId}/codespace/status`
   - Returns repo metadata, last test summary, and `codespaceUrl` as a `codespaces.new` deep link (no GitHub API side effects).

Talent Partner endpoints include repo/commit/workflow/diff URLs for detail and list views.

## Artifact contract (Actions -> Backend)
- Preferred artifact names (case-insensitive): `winoe-test-results`, `test-results`, `junit`.
- Artifact zip should contain `winoe-test-results.json` shaped as:
  ```json
  { "passed": 3, "failed": 1, "total": 4, "stdout": "...", "stderr": "", "summary": {...} }
  ```
- Fallback: any JSON with `passed/failed/total`; else JUnit XML (counts tests).

## Required environment
- `WINOE_GITHUB_API_BASE` (default `https://api.github.com`)
- `WINOE_GITHUB_ORG`
- `WINOE_GITHUB_TOKEN` (bot/app token with repo + actions)
- `WINOE_GITHUB_ACTIONS_WORKFLOW_FILE` (defaults to `winoe-evidence-capture.yml`)
- `WINOE_GITHUB_REPO_PREFIX`

## YC demo checklist
- Create or recover candidate repos with the correct workflow file.
- Ensure Actions workflow uploads the artifact described above.
- Configure env vars (above) and restart backend.
- Run candidate flow end-to-end: init codespace, run tests, submit; verify talent_partner list/detail show repo/commit/workflow links and parsed evidence counts.
