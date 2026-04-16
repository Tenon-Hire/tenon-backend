# Make Trial termination transactional and clean up workspaces, invites, and jobs #284

## Title
Make Trial termination transactional and clean up workspaces, invites, and jobs #284

## TL;DR
Trial termination now runs inside a transaction, marks the Trial as `terminated`, blocks new invites, and creates a single idempotent cleanup job that is reused on reruns. The cleanup path expires pending `not_started` candidate sessions, cancels/dead-letters trial-scoped jobs, archives/deletes candidate workspace repos through the canonical cleanup record, revokes GitHub direct collaborator access, and persists the workspace cleanup fields required for auditability.

## Problem
The previous cleanup handler was a no-op skeleton returning `{"status":"noop"}`, which meant terminating a Trial did not reliably stop new work, did not clean up candidate workspaces, did not revoke GitHub access, and did not cancel queued or running trial-scoped jobs. That left the Trial lifecycle inconsistent and made termination unsafe to rerun.

## What changed
- Trial termination is now transactional.
- Termination sets the Trial state to `terminated`.
- Terminated Trials block new invites.
- Pending `not_started` candidate sessions are expired on termination.
- Pending/running trial-scoped jobs are cancelled or dead-lettered during cleanup.
- A single idempotent Trial cleanup job is created and reused across reruns.
- Trial cleanup follows the canonical cleanup path to archive/delete candidate workspace repos.
- Trial cleanup revokes GitHub direct collaborator access.
- Workspace cleanup fields are populated on the canonical cleanup record.
- Termination and cleanup reruns are idempotent.

## Why this approach
The termination path needs to be safe under retries and partial failure. Making termination transactional ensures the Trial state change and cleanup scheduling stay consistent. Reusing one canonical cleanup job avoids duplicate side effects across reruns, and routing all repository cleanup through the canonical cleanup record keeps workspace state, GitHub actions, and audit fields aligned.

## Test plan
- `bash precommit.sh`
- Final result: `1697 passed, 13 warnings`
- Coverage: `96.20%`

## Manual QA evidence
- Real backend API used.
- Real GitHub used, not a mock.
- Trial creation, activation, invite, and terminate flow were exercised end to end.
- `POST /api/trials/26/terminate` returned terminated with cleanup job id `001a7fb9-0aec-4fb8-93ba-142be4438019`.
- Repeated terminate returned the same cleanup job id.
- Candidate session `37` moved to `expired`.
- Canonical workspace group row for `winoe-ai-repos/winoe-ws-37` showed:
  - `cleanup_status=archived`
  - `cleanup_attempted_at` populated
  - `cleaned_at` populated
  - `access_revoked_at` populated
  - `retention_expires_at` populated
  - `cleanup_error=null`
- Live GitHub repo `winoe-ai-repos/winoe-ws-37` was archived.
- `RobelKDev` appeared in `affiliation=direct` before cleanup and disappeared from `affiliation=direct` after cleanup.
- Post-termination invite attempts were blocked.
- Trial cleanup job succeeded and was reused idempotently.
- Collaborator revocation was exercised through a seeded `CandidateDayAudit` cutoff row so the real revocation branch executed.
- The queued/running job cancellation proof used a synthetic trial-scoped probe job because the scenario generation job had already succeeded during QA.

## Risks / reviewer notes
- Live GitHub QA showed direct collaborator revocation by confirming the collaborator disappeared from `affiliation=direct`.
- Any remaining visibility in `affiliation=all` after cleanup was inherited org/team/admin access, not direct collaborator access.
- Grouped workspace cleanup is canonical. Duplicate legacy workspace rows for the same repo key are intentionally skipped and are not a blocker.
- Cleanup reruns are designed to be idempotent, so repeated terminate requests should return the same cleanup job id and avoid duplicate side effects.

## Follow-ups / non-blockers
- Continue monitoring cleanup telemetry for repeated termination attempts and workspace cleanup retries.
- Keep the canonical workspace cleanup path as the only place that mutates repository archive/revocation state.
