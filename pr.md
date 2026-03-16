## Title
P2 Privacy/Compliance: Retention + consent + deletion workflows for media and candidate artifacts (#215)

## TL;DR
- Shipped candidate consent endpoint + persistence (`consent_version`, `consent_timestamp`, optional `ai_notice_version`).
- Enforced consent gate before Day 4 upload finalize (`409` if consent is missing).
- Shipped candidate-owned, idempotent delete endpoint for recordings.
- Blocked recruiter download URL/transcript access after delete or purge.
- Added retention settings and MVP manual/admin purge path (`POST /api/admin/media/purge`).
- Enforced short-lived signed URL TTL with bounded config validation/clamping.
- Added privacy-safe logging for consent/delete/purge events without transcript text, signed URLs, or bearer payload leakage.
- Manual/runtime QA verdict: PASS on real localhost FastAPI + fresh dedicated Postgres.

## Why
Day 4 uploads and transcripts introduced sensitive candidate artifacts. MVP required minimum viable privacy/compliance controls: explicit consent capture, deletion, retention enforcement, and short-lived signed URL access.

## What changed
### Consent capture and enforcement
- Added `POST /api/candidate/session/{candidate_session_id}/privacy/consent`.
- Persisted consent on candidate sessions (`consent_version`, `consent_timestamp`, optional `ai_notice_version`).
- Enforced consent before upload finalize; non-consented finalize is blocked with `409`.
- Propagated consent metadata to recording rows during upload flow.

### Candidate deletion workflow
- Added `POST /api/recordings/{recording_id}/delete`.
- Candidate ownership is enforced against the recording’s session.
- Delete is soft and idempotent: sets `status=deleted` and `deleted_at`, returns `{ "status": "deleted" }` on repeat calls.
- Transcript access is revoked on delete (transcript hidden from recruiter views, transcript payload cleared/marked deleted in DB).

### Signed URL enforcement
- Signed URL expiry is mandatory and bounded by settings.
- TTL uses clamp logic (`resolve_signed_url_ttl`) before URL generation.
- Default config remains short-lived (`SIGNED_URL_EXPIRY_SECONDS=900`, upper bound `<=1800`).
- Runtime QA config used stricter bounds (`SIGNED_URL_EXPIRY_SECONDS=120`, min `60`, max `300`) and observed `expiresIn=120`.

### Recruiter access hardening
- Existing recruiter company-ownership checks remain enforced.
- Deleted/purged media no longer returns recruiter download URLs or transcript payloads.
- Cross-company access remains forbidden.

### Retention and purge
- Added retention controls (`MEDIA_RETENTION_DAYS`, `MEDIA_DELETE_ENABLED`).
- Added MVP manual/admin purge endpoint: `POST /api/admin/media/purge`.
- Purge service removes storage object, hard-deletes transcript rows, and marks recordings `purged` with `purged_at`.
- Retention cutoff is anchored to `recording_assets.created_at`.

### Observability / logging
- Privacy events logged for consent recorded, recording deleted, purge executed.
- Logging intentionally excludes transcript text, signed URLs, and sensitive bearer/token payloads.

### Tests and manual QA
- Automated lint/test gates passed (details in Testing section).
- Manual/runtime QA passed with artifact-backed HTTP + SQL evidence bundle.

## API changes
- `POST /api/candidate/session/{candidate_session_id}/privacy/consent`
  - Payload:
    ```json
    { "noticeVersion": "mvp1" }
    ```
  - Response:
    ```json
    { "status": "consent_recorded" }
    ```
  - Notes: candidate-owned session required; consent version/timestamp (+ optional AI notice version) recorded.
- `POST /api/recordings/{recording_id}/delete`
  - Response:
    ```json
    { "status": "deleted" }
    ```
  - Notes: candidate-only, ownership enforced, idempotent.
- `POST /api/admin/media/purge`
  - Purpose: manual/admin-triggered retention purge path for MVP (not scheduler-driven in this issue).
  - Notes: accepts retention/batch controls and returns purge counts/IDs.
- Upload finalize now requires recorded consent.
- Deleted/purged assets do not return recruiter download URLs or transcript payloads.

## Data model / migration changes
- Migration: `alembic/versions/202603150002_add_media_privacy_controls.py`.
- Candidate session consent fields:
  - `candidate_sessions.consent_version`
  - `candidate_sessions.consent_timestamp`
  - `candidate_sessions.ai_notice_version`
- Recording delete/purge/consent fields:
  - `recording_assets.deleted_at`
  - `recording_assets.purged_at`
  - `recording_assets.consent_version`
  - `recording_assets.consent_timestamp`
  - `recording_assets.ai_notice_version`
- Transcript delete marker:
  - `transcripts.deleted_at`
- Recording status constraint expanded to include `deleted` and `purged`.

## Security / compliance notes
- Candidate delete is candidate-owned and enforced by ownership checks.
- Unauthorized delete attempts return `403`.
- Recruiters cannot delete candidate recordings; no recruiter/admin override-delete flow was added in this issue.
- Cross-company recruiter access remains forbidden.
- Deleted/purged assets cannot generate signed URLs.
- Signed URLs are short-lived and bounded by enforced min/max config.
- Logs exclude transcript text, signed URLs, and sensitive bearer/token payloads.

## Retention behavior
- Retention is anchored to `recording_assets.created_at`.
- `MEDIA_RETENTION_DAYS` defines the window (default `45` days for MVP).
- Purge is manual/admin-triggered for MVP (`POST /api/admin/media/purge`).
- Purge marks recordings as `purged` (`purged_at`, and `deleted_at` when needed) and removes transcript rows.
- HTTP QA evidence proves purge endpoint behavior and DB-side purge effects.
- Explicit storage-object removal proof was verified via direct purge-service invocation using the same DB/config and fake provider; this was not overclaimed as HTTP-only proof.

## Testing
- `poetry run ruff format --check .` -> PASS
- `poetry run ruff check .` -> PASS
- `poetry run pytest -q` -> PASS
- Final verified full-suite result: `1543 passed`
- Coverage: `99.01%`

## Manual QA / Runtime Verification
- Verdict: PASS.
- Runtime method:
  - Real FastAPI server on `127.0.0.1:8015`.
  - Fresh dedicated Postgres DB: `tenon_issue215_manualqa_20260316_133908`.
  - Migrations applied to head successfully (including `202603150002`).
- Evidence bundle path:
  - `.qa/issue215/manual_qa_20260316T133908Z/`
- Real HTTP + SQL/runtime evidence captured for:
  - Consent endpoint records consent fields.
  - Finalize without consent is blocked (`409`).
  - Consented finalize passes consent gate (then fails at expected downstream check: `422 Uploaded object not found` in fake-provider QA setup).
  - Candidate delete is idempotent.
  - Other-candidate delete attempt returns `403`.
  - Recruiter delete attempt returns `403`.
  - Recruiter access is removed after delete (`downloadUrl: null`, transcript hidden).
  - Admin/manual purge path works (`purgedCount=1`; recruiter sees purged asset with no download/transcript).
  - Signed URL TTL observed as short-lived (`expiresIn=120`).
  - Privacy logging checks found no transcript/signed URL/token leakage.

## Important QA nuance
- Candidate shorthand dev bearer tokens (`candidate:<email>`) were insufficient for candidate ownership checks in real HTTP QA because they lacked `email_verified`.
- Manual QA used signed JWTs from a local mock JWKS for candidate-endpoint runtime verification.
- This is a QA/runtime auth setup nuance, not a product-code blocker.

## Logging nuance
- Default server access logs in this run did not surface app-level privacy info events.
- Privacy-event verification was completed via a runtime log probe against the same DB/runtime configuration.

## Acceptance criteria mapping
1. Consent recorded before upload finalize: implemented via consent endpoint and verified with HTTP + SQL evidence (`A_*` consent artifacts).
2. Upload blocked if consent not recorded: implemented and verified (`B_complete_blocked_without_consent_*` returned `409`).
3. Deleted assets cannot generate download URLs: implemented and verified (post-delete recruiter response has `downloadUrl: null`).
4. Recruiter cannot access deleted asset: implemented and verified (post-delete recruiter response hides transcript and URL).
5. Retention purge path exists and removes storage objects: implemented with manual/admin purge endpoint + DB purge evidence; explicit storage removal proven via direct service invocation on same DB/config (`F_direct_service_*` artifacts).
6. Signed URLs expire and are not long-lived: implemented and verified with bounded TTL config and observed runtime `expiresIn=120`.

## Risks / rollout notes
- Purge is manual/admin-triggered for MVP; no scheduled job wiring is included here.
- QA runtime used fake storage provider.
- No frontend contract changes in this issue.
- No recruiter/admin override-delete flow was added (explicitly out of scope).

## Demo / QA checklist
1. Record consent via candidate consent endpoint.
2. Verify consent fields in DB.
3. Attempt upload finalize without consent and verify it is blocked.
4. Delete video as the owning candidate (repeat delete to confirm idempotency).
5. Verify recruiter playback/download access fails (`downloadUrl: null`, transcript hidden).
6. Trigger admin purge in test environment.
7. Confirm signed URL TTL is short-lived and bounded.
