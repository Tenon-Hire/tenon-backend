# MVP1 Operator Checklist (Internal)

Use this checklist before invites, during active evaluations, and before sharing winoe-report outputs.

## A. Pre-invite controls

- [ ] Confirm an active scenario version is set for the trial (`active_scenario_version_id`).
- [ ] Confirm the active scenario version is invite-ready/locked before sending invites.
- [ ] Confirm AI notice/toggle policy is correct on the trial:
  - `ai_notice_version`
  - `ai_notice_text`
  - `ai_eval_enabled_by_day`

## B. Evidence basis controls

- [ ] Confirm day 2 and day 3 cutoff audits were captured after window close:
  - `candidate_day_audits.cutoff_commit_sha`
  - `candidate_day_audits.eval_basis_ref`
  - `candidate_day_audits.cutoff_at`
- [ ] Confirm submission/talent_partner views show cutoff basis fields (`cutoffCommitSha`, `evalBasisRef`) where applicable.
- [ ] Confirm winoe-report run metadata contains basis data (`basisRefs`, `basis_fingerprint`) for traceability.

## C. Day 4 consent and media controls

- [ ] Confirm candidate consent was recorded before handoff upload completion:
  - `candidate_sessions.consent_version`
  - `candidate_sessions.consent_timestamp`
  - `candidate_sessions.ai_notice_version`
- [ ] Confirm retention/deletion policy matches environment settings:
  - `MEDIA_RETENTION_DAYS`
  - `MEDIA_DELETE_ENABLED`

## D. Re-run triggers

- [ ] Re-run evaluation (`POST /api/candidate_sessions/{candidate_session_id}/winoe_report/generate`) after any scenario-version change that should affect scoring context.
- [ ] Re-run evaluation after any change that affects cutoff basis for day 2/3.
- [ ] Confirm the latest run is the one used for review (`GET /api/candidate_sessions/{candidate_session_id}/winoe_report`).

## E. Manual override and audit controls

- [ ] Do not perform manual override/reset actions for evaluated sessions without explicit override intent (`overrideIfEvaluated`) and a documented reason.
- [ ] For admin demo-ops actions that use the audit pipeline (session reset, job requeue, scenario fallback), confirm response `auditId` values have matching `admin_action_audits` records.
- [ ] Confirm no out-of-band manual data edits were made without a corresponding audit trail entry.
