# Harden empty-repo GitHub provisioning and evidence capture

## Summary

This PR hardens GitHub provisioning for the v4 from-scratch Tech Trial flow.

Candidate workspaces are now created as empty repos and initialized only with Winoe-owned workspace files. Candidate GitHub username is required before workspace provisioning, collaborator permissioning uses that username, evidence capture runs through the canonical workflow `.github/workflows/winoe-evidence-capture.yml`, stable evidence artifact names are parsed reliably, and cleanup is bounded and idempotent.

## What changed

- Empty-repo repo creation and recovery path for candidate workspaces.
- Required bootstrap files are created in the repo:
  - `.devcontainer/devcontainer.json`
  - `README.md`
  - `.gitignore`
  - `.github/workflows/winoe-evidence-capture.yml`
- Devcontainer defaults to the Microsoft universal image unless a language-specific image is selected for the Talent Partner's preferred language.
- `README.md` is used as the Project Brief.
- No app starter code is added to candidate repos.
- Generated `.gitignore` does not ignore lockfiles.
- Candidate GitHub username is required before provisioning continues.
- Collaborator add behavior is retried safely when permissioning already exists or was partially applied.
- Evidence workflow and artifact parser behavior were updated for the new canonical workflow and stable artifact names.
- Invite and preprovision cleanup paths are more precise so they only remove resources created during the current attempt.
- Retry and idempotency paths are covered by tests.
- Documentation was updated to match the v4 empty-repo provisioning flow.

## v4 pivot alignment

- No generated-from-template repo path is used in active provisioning.
- No template catalog dependency is used in active provisioning.
- No precommit bundle is applied to candidate repos in the v4 path.
- No Codespace Specializor or Specializer component is used.
- The repo is evaluated as candidate-authored from scratch.

This wording reflects the active path only. It does not claim historical compatibility code was removed unless the implementation actually changed it.

## Evidence / artifacts

Canonical artifact names:

- `winoe-commit-metadata`
- `winoe-file-creation-timeline`
- `winoe-repo-tree-summary`
- `winoe-dependency-manifests`
- `winoe-test-detection`
- `winoe-test-results`
- `winoe-lint-detection`
- `winoe-lint-results`
- `winoe-evidence-manifest`

Canonical JSON files:

- `commit_metadata.json`
- `file_creation_timeline.json`
- `repo_tree_summary.json`
- `dependency_manifests.json`
- `test_detection.json`
- `test_results.json`
- `lint_detection.json`
- `lint_results.json`
- `evidence_manifest.json`

Wrapper schema fields:

- `schema_version`
- `repository_full_name`
- `commit_sha`
- `workflow_run_id`
- `generated_at`
- `status`
- `payload`

Test and lint detection distinguishes:

- `detected`
- `not_detected`
- failed command execution as evidence

## Idempotency and recovery

- Provisioning retry reuses the existing repo and workspace.
- Missing bootstrap files are repaired.
- Missing workflow files are repaired.
- Collaborator add is safe on retry.
- Codespace creation and recovery paths are retried safely.
- Duplicate workspace groups and workspaces are avoided.
- Day 2 and Day 3 share the canonical coding repo where expected.

## Cleanup behavior

- Cleanup is idempotent.
- Invite rollback cleanup only targets repos created during the current attempt.
- Existing or reused repos are not deleted accidentally.
- Trial termination cleanup remains scoped to the Trial and workspace.
- Already-cleaned resources are handled safely.

## QA evidence

```text
QA PASS — ready for PR prompt

Environment:
- Branch: feature/harden-github-provisioning-for-empty-repo-codespace-creation-and-evidence-capture
- Commit: d39e7dbf0b091bc239d4d50870d8d52a4af00d0b
- Backend command: ./scripts/local_qa_backend.sh
- Worker command: python -m app.shared.jobs.shared_jobs_worker_cli_service worker
- Backend health: GET /health returned {"status":"ok"}
- Worker readiness: GET /ready returned ready with fresh worker heartbeat

Manual QA covered:
- missing GitHub username gate
- username-present provisioning
- repo contents inspection
- idempotent retry
- partial recovery
- evidence workflow contract
- artifact parsing/retrieval
- cleanup/termination
- retired-terminology active-path check
```

```text
Live GitHub push execution was not performed in this QA pass. Route probes used an in-memory stub GitHub provider. GitHub Actions workflow execution was verified by workflow YAML contract and backend tests; artifact parsing/retrieval was verified through backend test paths.
```

## Validation

```text
bash ./precommit.sh
✅ passed
1865 passed, 13 warnings
Coverage: 96.00%
Required coverage: 96%
```

```text
git diff --check
✅ passed
```

## Risks / limitations

- Live GitHub push execution was not performed in this QA pass.
- Evidence capture execution was verified through workflow contract checks and backend tests rather than a live GitHub Actions run.
- Cleanup correctness depends on the repo/workspace identifiers returned by the current attempt, so future changes to those identifiers should be revalidated.

## Issue checklist

- [x] Empty repo creation is idempotent and safe to retry
- [x] Repo initialized with `.devcontainer/devcontainer.json`, `README.md`, `.gitignore`, and evidence-capture Actions workflow
- [x] Devcontainer uses Microsoft universal image by default
- [x] Recovery from partial GitHub API failure / partial repo initialization
- [x] Candidate username-based permissioning via collaborator add
- [x] GitHub Actions evidence-capture workflow runs on push
- [x] Workflow captures commit metadata, file creation order, test detection, and linting results
- [x] Evidence artifacts are uploaded and parseable/retrievable through backend paths
- [x] Cleanup on Trial termination is idempotent and scoped

## PR title

Harden empty-repo GitHub provisioning and evidence capture

Worker Report:
- Summary
  - Updated `pr.md` only to describe the v4 empty-repo GitHub provisioning and evidence capture flow.
- Files changed
  - `pr.md`
- Commands run
  - `git status --short` - pass
  - `git diff --check` - pass
  - `bash ./precommit.sh` - pass
  - `git diff --check` - pass
- Risks / assumptions
  - Assumed the provided QA and validation text is the canonical PR-materials source.
  - Kept the document aligned to the active v4 path and avoided retired product language in the main narrative.
- Open questions / blockers
  - None
