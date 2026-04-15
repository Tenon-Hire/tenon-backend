# Fix GitHub template generation redirects and destination-org repo creation #282
Closes #282.

## 2. TL;DR
This PR fixes GitHub template generation and provisioning so the backend resolves the real canonical template repos under `winoe-ai-repos`, follows redirects during template generation, and creates candidate repos in the configured destination org. Canonical template catalog entries now point at `winoe-ai-template-*`, backward normalization still accepts stale historical values, and repo identity validation is strict on owner, name, and `full_name`. Manual live QA confirmed the end-to-end Talent Partner flow and the created repo state.

## 3. Problem
GitHub template generation had two production-impacting issues:
- The requests client used for template generation did not reliably follow redirects.
- Candidate repos could be provisioned under the wrong org instead of the configured destination org, `WINOE_GITHUB_ORG` / `winoe-ai-repos`.

That created two failure modes:
- Template catalog entries could become unreachable or resolve incorrectly.
- Provisioning could create the workspace repo in the wrong org, which breaks the invite and coding flow.

## 4. What changed
- Canonical template catalog entries now reference the real repos under `winoe-ai-repos` using the `winoe-ai-template-*` naming.
- Backward normalization was preserved for stale historical template values, including:
  - `winoe-hire-dev/...`
  - `winoe-ai-repos/winoe-template-*`
- Destination-org provisioning is enforced to `WINOE_GITHUB_ORG` / `winoe-ai-repos`.
- Repo identity validation now checks `owner`, `name`, and `full_name` strictly before treating a GitHub repo as the expected destination.
- Template generation is redirect-aware so template repo resolution follows GitHub redirects instead of failing on the initial response.
- Template-health checks now resolve against the real canonical repositories instead of stale or redirected names.

## 5. Scope / notable implementation details
- This change is intentionally scoped to GitHub template resolution and provisioning correctness.
- The normalization logic keeps older stored values readable, but the canonical source of truth is now the real repo set under `winoe-ai-repos`.
- The repo validation logic is strict by design so provisioning does not silently accept a repo owned by the wrong org or with a mismatched identity.
- The template-health path now checks the same canonical repo targets used by provisioning, which keeps health output aligned with real runtime behavior.
- This PR does not broaden the GitHub provisioning surface beyond the acceptance criteria for #282.

## 6. Test plan
- Start the backend API and worker.
- Confirm readiness after startup with `GET /ready`.
- Confirm template-health succeeds with `GET /api/admin/templates/health?mode=static`.
- Run a live Talent Partner flow through trial creation, scenario approval, trial activation, and candidate invite.
- Verify the provisioned repo exists in GitHub under the destination org and matches the expected repository metadata.
- Verify the persisted database rows store the canonical template and repo full names.

## 7. Manual QA
Manual live QA succeeded end to end.

Verified sequence:
- Backend API and worker started successfully.
- `GET /ready` returned healthy after worker startup.
- `GET /api/admin/templates/health?mode=static` returned success with all catalog entries healthy.
- Live Talent Partner flow succeeded:
  - Trial created
  - scenario approved
  - Trial activated
  - candidate invited

Provisioning and repo verification:
- Live provisioning created `winoe-ai-repos/winoe-ws-13-coding`
- Source template repo used: `winoe-ai-repos/winoe-ai-template-python-fastapi`
- GitHub API confirmed the created repo exists, is private, and has `default_branch=main`
- DB evidence confirmed persisted workspace/workspace_group rows with:
  - `template_repo_full_name=winoe-ai-repos/winoe-ai-template-python-fastapi`
  - `repo_full_name=winoe-ai-repos/winoe-ws-13-coding`

Non-blocking note:
- Invite email delivery logged `email_send_failed`.
- That did not block repo creation or provisioning and is separate from the #282 scope.

## 8. Risks / follow-ups
- Any future GitHub template added to the catalog must follow the same canonical naming and redirect-safe resolution rules.
- The backward normalization exists to protect old stored values; new writes should use the canonical `winoe-ai-template-*` names only.
- Email delivery remains a separate follow-up item because it did not block the repo provisioning path verified here.

## 9. Notes for reviewers
- Review the canonical repo name changes first: `winoe-ai-template-*` under `winoe-ai-repos`.
- The important behavioral checks are redirect handling, strict repo identity validation, and destination-org enforcement.
- The manual QA evidence is the main end-to-end proof for this PR; the email send failure is explicitly out of scope for this issue.
