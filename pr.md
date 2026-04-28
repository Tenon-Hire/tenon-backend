## Summary

Implement policy-driven media retention and purge scheduling for Day 4 media artifacts.

This PR adds configurable retention metadata, an expired-media purge path, privacy-safe purge audit records, and a scoped data-request deletion hook. The purge flow redacts transcript content while preserving auditability and Evidence Trail shape.

## What changed

- Added configurable media retention via `MEDIA_RETENTION_DAYS`.
- Added retention expiration and purge metadata to recording assets.
- Added media purge audit records for retention and data-request purges.
- Added expired-media purge service behavior.
- Registered the `media_retention_purge` shared worker handler.
- Added script/operator paths for triggering retention purge.
- Added scoped data-request media purge support for Candidate sessions.
- Redacted transcript text/segments during purge instead of silently hard-deleting transcript rows.
- Preserved idempotency for already-purged media and missing storage objects.
- Added tests for config, retention selection, purge behavior, audit records, worker registration, operator route behavior, missing storage, and data-request scoping.

## Acceptance criteria

- [x] Configurable retention period
  - `MEDIA_RETENTION_DAYS` is configurable.
  - Default remains `45`, matching the existing repo convention.
  - Invalid values such as `0` are rejected.

- [x] Purge job for expired media
  - Expired media is selected by retention metadata.
  - Purge runs through the media privacy service.
  - `media_retention_purge` is registered with the shared worker runtime.
  - Admin/operator and script trigger paths are available.
  - Purge is idempotent and safe to rerun.

- [x] Audit log for purge events
  - `media_purge_audits` records purge attempts.
  - Audit rows include media, Candidate session, Trial, actor, reason, outcome, and safe error summary where applicable.
  - Worker/system purges use `actor_type=system`.
  - Operator-triggered purges use `actor_type=operator`.
  - Audit records do not include signed URLs, credentials, tokens, or raw transcript body.

- [x] Deletion workflows for data requests
  - Added `purge_candidate_session_media_for_data_request(...)`.
  - Data-request purge is scoped to the requested Candidate session.
  - Unrelated Candidate/Trial media is not touched.
  - Reruns are idempotent.
  - Audit reason is `data_request`.

## QA evidence

### Migration / schema

- `poetry run alembic upgrade head` passed.
- `poetry run alembic heads` returned `202604200001 (head)`.
- Verified schema:
  - `recording_assets.retention_expires_at`
  - `recording_assets.purge_reason`
  - `recording_assets.purge_status`
  - existing `recording_assets.purged_at`
  - `media_purge_audits`
- Verified indexes:
  - `ix_recording_assets_retention_expires_purged`
  - `ix_media_purge_audits_media_created_at`
  - `ix_media_purge_audits_reason_created_at`
  - `ix_media_purge_audits_candidate_session_created_at`

### Config verification

- `poetry run pytest --no-cov -q tests/config/test_config_storage_media_settings_utils.py`
  - `11 passed in 0.59s`
- Runtime checks:
  - default `MEDIA_RETENTION_DAYS = 45`
  - override `MEDIA_RETENTION_DAYS=7` works
  - invalid `MEDIA_RETENTION_DAYS=0` is rejected

### Focused automated tests

- `poetry run pytest --no-cov -q tests/config tests/media tests/shared/jobs tests/talent_partners/routes/test_talent_partners_admin_media_purge_routes.py tests/integrations/storage_media/test_integrations_storage_media_s3_provider_delete_object_handles_success_and_missing_service.py`
  - `332 passed in 19.34s`

- Previously failing direct test:
  - `poetry run pytest --no-cov -q tests/media/repositories/test_media_repositories_recordings_repository_retention_helpers_repository.py`
  - `2 passed in 0.33s`

### Full regression / precommit

- `./precommit.sh`
  - `1857 passed, 13 warnings`
  - coverage `96.02%`
  - required coverage `96%` reached
  - all precommit checks passed

- `git diff --check`
  - passed

## Manual QA evidence

### Retention purge success path

Seeded:
- Talent Partner
- Trial
- Candidate session
- Day 4 handoff task
- ready media asset
- transcript with text/segments
- fake storage object
- expired `retention_expires_at`

Observed:
- `scanned_count=1`
- `purged_count=1`
- `failed_count=0`
- media `status=purged`
- `purge_reason=retention_expired`
- `purge_status=purged`
- `purged_at` set
- transcript row still exists
- transcript `text=null`
- transcript `segments_json=null`
- transcript `deleted_at` set
- storage object removed
- audit row written with `outcome=success`
- audit actor type `system`
- audit actor id `null`
- Candidate session and Trial context present

### Day 4 upload retention metadata

Verified Day 4 upload completion sets retention metadata:
- `status=uploaded`
- `retention_expires_at` set
- retention delta matches `45` days

### Idempotent rerun

Second purge against already-purged media:
- `scanned_count=0`
- `purged_count=0`
- `failed_count=0`
- media stayed purged
- transcript stayed redacted
- audit count remained stable

### Missing storage object behavior

Seeded two expired assets:
- one missing from storage
- one present in storage

Observed:
- `scanned_count=2`
- `purged_count=2`
- `failed_count=0`
- both media records became purged
- both transcripts redacted
- audit rows written with `outcome=success`
- missing object did not fail the batch

### Operator-triggered purge

Direct admin route invocation returned:
- `status=ok`
- `scannedCount=1`
- `purgedCount=1`
- `skippedCount=0`
- `failedCount=0`

Audit verified:
- `actor_type=operator`
- `actor_id=admin-qa-306`
- `purge_reason=retention_expired`

### Shared worker/system purge

Verified:
- `media_retention_purge` handler is registered.
- Payload maps `batchLimit` and `retentionDays`.
- Worker result:
  - `scannedCount=1`
  - `purgedCount=1`
  - `skippedCount=0`
  - `failedCount=0`

Audit verified:
- `actor_type=system`
- `actor_id=null`
- `purge_reason=retention_expired`

### Data-request deletion hook

Seeded Candidate session A and B under the same Trial.

Ran `purge_candidate_session_media_for_data_request(...)` for Candidate session A only.

Observed:
- Candidate session A media purged.
- Candidate session A transcript redacted.
- Candidate session A audit reason `data_request`.
- Candidate session A audit actor `operator`.
- Candidate session A audit actor id `privacy-qa-operator`.
- Candidate session B media remained uploaded.
- Candidate session B transcript remained untouched.
- Candidate session B had no audit row.
- Rerun for Candidate session A returned no additional purge work.

## Security / privacy

Verified #306 manual QA logs and audit rows do not contain:
- signed URLs
- access tokens
- storage credentials
- raw transcript body
- raw transcript segments
- full exception traces in operator-facing output

## Terminology check

Changed-file terminology scan passed with zero hits for retired terms.

## Notes / limitations

- No app-level periodic scheduler/cron cadence exists in this repo.
- This PR provides the registered shared worker handler, operator/admin trigger path, and script trigger path.
- Deployment cadence for invoking the idempotent purge job remains an ops concern.

## Risk

Low-to-medium.

The purge path touches privacy-sensitive media and Evidence Trail artifacts, so the risk is primarily around data deletion correctness and auditability. Manual QA covered success, rerun idempotency, missing storage, operator/system actor semantics, and scoped data-request deletion.

## Rollback

Revert this PR and run Alembic downgrade according to repo migration conventions if needed. Existing media records are only purged when the purge job/operator path runs; the migration itself adds metadata/audit structures and backfills retention timestamps.

Fixes #306
