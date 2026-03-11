# Issue #211: Day 4 Media Upload, Transcription, and Recruiter Retrieval

## TL;DR
- Day 4 now supports end-to-end media flow: upload init, direct upload complete, transcription job execution, and recruiter evidence retrieval.
- Completing upload updates `submission.recording_id` and enqueues durable `transcribe_recording`.
- Worker persists transcript `text` plus timestamped `segments`, and updates recording/transcript lifecycle status.
- Recruiter submission detail returns pointer-based handoff media/transcript data with short-lived signed download URLs.
- Manual/runtime QA verdict is **PASS**, with A-K scenarios verified and evidence archived under `.qa/issue211/`.

## Problem / Why
Day 4 previously lacked a complete media evidence pipeline. Candidates could not finish a supported upload-to-transcript loop, and recruiters could not reliably retrieve playback and transcript evidence from submission detail. This change closes that gap for MVP Day 4 handoff.

## What changed

### API endpoints
- Added candidate endpoints:
  - `POST /api/tasks/{task_id}/handoff/upload/init`
  - `POST /api/tasks/{task_id}/handoff/upload/complete`
  - `GET /api/tasks/{task_id}/handoff/status`
- Extended `GET /api/submissions/{submission_id}` to include handoff recording + transcript data.

### Schema / migration
- Added `submissions.recording_id` (FK to `recording_assets.id`) and index `ix_submissions_recording_id`.
- Added `transcripts.last_error` for failed transcription diagnostics.
- Migration: `alembic/versions/202603110001_add_submission_recording_pointer_and_transcript_last_error.py`.

### Transcription job wiring
- Upload complete enqueues durable `transcribe_recording` with idempotency key `transcribe_recording:{recording_id}`.
- Worker handler:
  - marks recording/transcript `processing`
  - signs source URL and invokes transcription provider
  - stores transcript `text`, `segments_json`, `model_name`
  - marks `ready` on success or `failed` with `last_error` on failure

### Recruiter retrieval payload
- Recruiter detail returns:
  - `recording` metadata + signed `downloadUrl` when downloadable
  - `transcript` with `status`, `text`, `segments`/`segmentsJson`, `modelName`
  - `handoff` convenience block with `recordingId`, `downloadUrl`, and nested transcript
- Retrieval is based on `submission.recording_id` (pointer-based).

### Resubmission behavior
- New upload init creates a new `RecordingAsset` attempt.
- Upload complete updates `submission.recording_id` to the new attempt.
- Historical attempts remain persisted for audit traceability.
- Candidate status resolves the latest attempt for the task/session.

### Auth / security / error handling
- Candidate init/complete enforce candidate auth, session ownership, handoff-task checks, and window gating.
- Candidate status endpoint remains readable post-cutoff for submitted attempts.
- Recruiter access enforces same-company authorization before media URL signing.
- Signed URLs are short-lived.
- Logging captures transitions and failures without logging signed URLs or transcript text.

## Important behavior / contracts
- Candidate upload init and complete are window-gated.
- Candidate `GET /api/tasks/{task_id}/handoff/status` remains readable after submission even after cutoff.
- Candidate status returns the latest attempt.
- Recruiter detail resolves media from `submission.recording_id`.
- Signed media URLs are generated only after recruiter authorization and are short-lived.
- Transcription failures persist as `transcript.status=failed` (with `last_error`) and `recording.status=failed`.

## Error handling
- `TASK_WINDOW_CLOSED` (409) when init/complete is outside the allowed window.
- `REQUEST_TOO_LARGE` (413) when uploaded object exceeds size limits (including complete-time validation).
- `MEDIA_STORAGE_UNAVAILABLE` (502) for storage signing/metadata failures.
- Transcription failures persist transcript `failed` state rather than failing the upload-complete API path.

## Testing
- `poetry run pytest -q` -> **PASS** (`1296 passed`, coverage `99.00%`).
- `poetry run ruff check .` -> **PASS**.
- Migration smoke rerun -> **PASS**.
- Targeted regression coverage includes:
  - latest-attempt candidate status contract
  - recruiter pointer-based media retrieval
  - wrong-company recruiter denial before URL issuance
  - oversize object complete-time 413 mapping
  - post-cutoff status readability

## Manual / Runtime QA
- Verdict: **PASS**.
- Runtime method: localhost server startup was blocked by sandbox bind restrictions; QA was executed via ASGI in-process fallback against real FastAPI app/routes/services/repos/worker codepaths.
- Evidence bundle:
  - `.qa/issue211/manual_qa_20260310_232634`
  - `.qa/issue211/manual_qa_20260310_232634.zip`
- Verified scenarios:
  - A. upload init - PASS
  - B. upload complete - PASS
  - C. worker transcription execution - PASS
  - D. recruiter retrieval - PASS
  - E. resubmission semantics - PASS
  - F. window gating - PASS
  - G. unauthorized recruiter denied - PASS
  - H. oversize enforcement - PASS
  - I. storage failure mapping - PASS
  - J. logging/security hygiene - PASS
  - K. migration confidence - PASS

## Migration / rollout notes
- Schema change includes `submissions.recording_id` and `transcripts.last_error`.
- Migration smoke rerun passed, providing confidence for upgrade/downgrade path.
- No frontend changes are required in this issue.

## Risks / follow-ups
- Transcription provider credentials/model configuration remain environment-specific operational setup in production.

## Reviewer notes
- Core candidate upload flow:
  - `app/api/routers/tasks/handoff_upload.py`
  - `app/services/media/handoff_upload.py`
- Transcription job/worker:
  - `app/jobs/handlers/transcribe_recording.py`
  - `app/jobs/worker.py`
- Recruiter submission detail:
  - `app/api/routers/submissions_routes/detail.py`
- Migration:
  - `alembic/versions/202603110001_add_submission_recording_pointer_and_transcript_last_error.py`
- Key tests:
  - `tests/api/test_handoff_upload_api.py`
  - `tests/integration/test_handoff_transcription_integration.py`
  - `tests/unit/test_submission_detail_media_route.py`
  - `tests/unit/test_transcribe_recording_handler.py`
