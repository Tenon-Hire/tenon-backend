# Title
Issue #210: Added object storage integration, signed media URLs, and recording/transcript persistence

## TL;DR
- Added pluggable media object storage integration under `app/integrations/storage_media` with `fake` and S3-compatible providers.
- Added candidate handoff upload init/complete flow backed by `recording_assets`, plus transcript placeholder creation on complete.
- Added `recording_assets` and `transcripts` models/repositories with migration-managed schema and status constraints.
- Added recruiter submission detail media payload (`recording`, `transcript`) with short-lived signed download URL generation.
- Enforced media security constraints: session/company auth boundaries, safe object key validation, TTL clamping, content type/size allowlists, and upload metadata verification before status transition.

## What changed
- **Storage abstraction**
  - Introduced `StorageMediaProvider` contract in `app/integrations/storage_media/base.py`:
    - `create_signed_upload_url(key, content_type, size_bytes, expires_seconds)`
    - `create_signed_download_url(key, expires_seconds)`
    - `get_object_metadata(key)` (used to verify completed uploads)
  - Added safe-key validation (`ensure_safe_storage_key`) and TTL clamping helper.
  - Added provider factory (`app/integrations/storage_media/factory.py`) with pluggable provider selection.

- **Signed upload/download URL support**
  - Added deterministic `FakeStorageMediaProvider` for local/test flows.
  - Added `S3StorageMediaProvider` implementing SigV4 query-signed URLs for upload/download and metadata HEAD checks.
  - Added TTL resolution/clamping via media settings (`MEDIA_SIGNED_URL_*`).

- **Recording/transcript models + migration**
  - Added `RecordingAsset` model + repository under `app/repositories/recordings/*`.
  - Added `Transcript` model + repository under `app/repositories/transcripts/*`.
  - Added migration `alembic/versions/202603100003_add_recording_assets_and_transcripts.py`.

- **Candidate upload init/complete endpoints**
  - Added:
    - `POST /api/tasks/{task_id}/handoff/upload/init`
    - `POST /api/tasks/{task_id}/handoff/upload/complete`
  - Added service orchestration in `app/services/media/handoff_upload.py`.
  - Added key generation/parsing in `app/services/media/keys.py` and upload validation in `app/services/media/validation.py`.

- **Recruiter submission detail media additions**
  - Extended recruiter submission detail route (`GET /api/submissions/{submission_id}`) to include:
    - latest recording metadata for the submission task/session
    - transcript metadata
    - signed download URL when recording status is downloadable
  - Extended schema outputs in `app/schemas/submissions.py` (`RecruiterRecordingAssetOut`, `RecruiterTranscriptOut`).

- **Upload-complete metadata verification**
  - `complete` flow now validates uploaded object exists and matches expected `content_type` and `size_bytes` before transitioning recording status from `uploading/failed` to `uploaded`.
  - Transcript placeholder row is created idempotently (`pending`) during completion.

- **Logging/security behavior**
  - Added structured logs for recording creation, upload completion, transcript placeholder creation, and download URL generation.
  - Logs intentionally exclude signed URLs and transcript text payloads.

## API contract
- **Candidate auth endpoints**
  - `POST /api/tasks/{task_id}/handoff/upload/init`
    - Request:
      - `contentType: string`
      - `sizeBytes: int (>0)`
      - `filename?: string`
    - Response:
      - `recordingId: string` (e.g., `rec_123`)
      - `uploadUrl: string`
      - `expiresInSeconds: int`
  - `POST /api/tasks/{task_id}/handoff/upload/complete`
    - Request:
      - `recordingId: string` (`rec_<id>` or positive integer string)
    - Response:
      - `recordingId: string`
      - `status: string`

- **Recruiter auth endpoint (existing, additive media fields)**
  - `GET /api/submissions/{submission_id}`
    - Adds `recording` and `transcript` payloads when present.
    - `recording.downloadUrl` is generated on request only for downloadable recording statuses.

- **Error behavior**
  - `403`:
    - candidate/recruiter auth boundary violations
    - candidate attempting to complete another candidate’s recording
    - recruiter attempting cross-company submission access
  - `404`:
    - nonexistent submission/recording
  - `422`:
    - invalid `contentType`, invalid file extension, invalid `sizeBytes`, invalid `recordingId`
    - non-handoff task upload attempt
    - uploaded object missing or metadata mismatch (size/type)
  - `503`:
    - storage provider unavailable for signed URL generation or metadata inspection

## Schema / migration
- Migration added:
  - `202603100003_add_recording_assets_and_transcripts.py`

- New table: `recording_assets`
  - Columns: `id`, `candidate_session_id`, `task_id`, `storage_key`, `content_type`, `bytes`, `status`, `created_at`
  - Constraints:
    - `uq_recording_assets_storage_key`
    - `ck_recording_assets_status` (`uploading|uploaded|processing|ready|failed`)
    - FKs to `candidate_sessions.id`, `tasks.id`
  - Indexes:
    - `ix_recording_assets_candidate_session_task_created_at`
    - `ix_recording_assets_candidate_session_id`
    - `ix_recording_assets_task_id`

- New table: `transcripts`
  - Columns: `id`, `recording_id`, `text`, `segments_json`, `model_name`, `status`, `created_at`
  - Constraints:
    - `uq_transcripts_recording_id`
    - `ck_transcripts_status` (`pending|processing|ready|failed`)
    - FK to `recording_assets.id`
  - Indexes:
    - `ix_transcripts_recording_id`
    - `ix_transcripts_status_created_at`

- Migration verification note:
  - Full `alembic upgrade head` on SQLite failed at unrelated historical migration `202506010001` (SQLite constraint ALTER limitation).
  - Issue #210 migration was verified directly with targeted `alembic stamp 202603100002` + `alembic upgrade 202603100003` on an isolated DB.
  - `recording_assets` and `transcripts` tables/columns/constraints/indexes were verified from isolated QA DB artifacts.

## Security / invariants
- Candidate endpoints require candidate auth and enforce task/session ownership.
- Recruiter submission detail enforces recruiter role + company boundary checks.
- Object keys are namespaced and traversal-safe via key builder + `ensure_safe_storage_key`.
- Signed URL TTL is bounded by settings (`MEDIA_SIGNED_URL_MIN_SECONDS` / `MEDIA_SIGNED_URL_MAX_SECONDS`).
- Signed URLs and transcript text are not logged.
- Upload completion never marks `uploaded` unless object metadata (existence, content type, size) matches expected recording metadata.

## Final verification results
- `poetry run ruff check .`: PASS
- `poetry run ruff format --check .`: PASS (`839 files already formatted`)
- `poetry run pytest -q`: PASS (`1262 passed in 66.96s (0:01:06)`)
- Coverage: `Required test coverage of 99% reached. Total coverage: 99.02%`

- Key targeted areas added/expanded:
  - Storage key safety, provider factory resolution, and S3 signing/error-path behavior.
  - Candidate upload init/complete route shapes and service authorization/validation/error handling.
  - Recording/transcript repository create/get/update/get-or-create behavior.
  - Recruiter submission detail media payload + signed download URL path and storage-failure handling.

## Manual QA
- Verdict: **PASS**
- Runtime method:
  - Localhost attempt failed due sandbox bind restriction.
  - ASGI in-process fallback was used against the real FastAPI app.
- Isolated QA environment:
  - `TENON_ENV=test`
  - Isolated runtime DB for scenario execution.
  - Isolated migration DB artifacts for schema verification.
  - Deterministic `FakeStorageMediaProvider`.

- Scenario checklist (all PASS):
  - A: candidate upload init success.
  - B: invalid metadata rejected with `422`.
  - C: candidate ownership enforcement with `403`.
  - D: complete upload success with object metadata verification.
  - E: complete upload idempotency.
  - F: missing object rejected with `422`.
  - G: size/content-type mismatch rejected with `422`.
  - H: authorized recruiter gets recording/transcript metadata plus signed download URL.
  - I: wrong-company recruiter denied with `403`.
  - J: storage/download failure path returns `503`.
  - K: signed URL TTL bounded and observed as expected.
  - L: logging hygiene verified (no full signed URLs, no transcript plaintext in logs).

### QA evidence
- Bundle: `.qa/issue210/manual_qa_20260310T234901Z`
- Report: `.qa/issue210/manual_qa_20260310T234901Z/QA_REPORT.md`
- Commands log: `.qa/issue210/manual_qa_20260310T234901Z/commands.log`
- Zip: `.qa/issue210/manual_qa_20260310T234901Z.zip`

## Risks / follow-ups
- Real object-store behavior may vary by provider around `Content-Type` normalization and HEAD metadata timing/availability.
- Unrelated SQLite full-head migration limitation exists outside Issue #210 scope.
- This limitation does not invalidate the Issue #210 feature manual QA result.
- Follow-up #211 (transcription job pipeline/orchestration) is intentionally out of scope for this PR.

## Rollout / demo checklist
- Candidate calls upload init endpoint and receives `recordingId` + signed `uploadUrl`.
- Client performs direct object storage upload.
- Candidate calls upload complete and recording status transitions to `uploaded`.
- Recruiter fetches submission detail and receives media metadata plus signed `downloadUrl` when authorized.
- Unauthorized candidate/recruiter paths return expected `403`/`404`/`422` behavior.
