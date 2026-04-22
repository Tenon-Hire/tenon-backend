## 1. Title

Harden Day 4 media upload, playback, transcription, and retention

## 2. Summary

This PR closes the backend slice of #294 for the Day 4 handoff/demo media path:

- signed Day 4 upload initiation is reliable for valid media
- playback and download URLs are built from the configured backend media base URL
- transcription now recovers when the provider top-level `text` is blank but segment text exists
- candidate and Talent Partner backend payloads expose visible transcript and job state
- CSP/media-origin coverage is driven from storage-media config for local and production bases
- retention and purge flows degrade safely instead of surfacing broken media state
- the Day 4 upload contract is tightened to `video/mp4` / `.mp4` only so the backend does not accept formats it cannot reliably transcribe end-to-end

## 3. Files Changed

Actual tracked files changed in this branch:

- `app/config/config_storage_media_config.py` - storage-media defaults and validation, including the mp4-only default contract.
- `app/media/services/media_services_media_validation_service.py` - upload validation now rejects unsupported Day 4 media at init.
- `app/shared/jobs/handlers/shared_jobs_handlers_transcribe_recording_runtime_handler.py` - transcription runtime fallback and retry handling.
- `tests/config/test_config_storage_media_settings_utils.py` - config validation coverage for retention, signed URL bounds, and mp4-only defaults.
- `tests/integrations/storage_media/test_integrations_storage_media_provider_service.py` - fake provider and signed URL base-path coverage.
- `tests/media/routes/test_media_handoff_upload_handoff_upload_end_to_end_routes.py` - end-to-end signed upload, playback URL, and transcript/job state coverage.
- `tests/media/routes/test_media_handoff_upload_handoff_upload_init_rejects_invalid_content_type_and_size_routes.py` - invalid content type and oversize rejection coverage.
- `tests/media/routes/test_media_handoff_upload_handoff_upload_init_success_routes.py` - signed upload init success coverage for valid `.mp4`.
- `tests/media/services/test_media_storage_media_service.py` - upload contract validation and storage key behavior.
- `tests/shared/http/test_shared_http_security_headers_utils.py` - media-origin CSP regression coverage.
- `tests/shared/jobs/handlers/test_shared_jobs_handlers_transcribe_recording_runtime_handler.py` - transcript reconstruction and retry-path coverage.

## 4. Key Implementation Details

- The transcription runtime now reconstructs transcript text from normalized segment text when the provider top-level `text` is blank, but it still fails terminally on truly empty transcripts.
- Fake/local storage playback URLs are config-driven, so signed download links resolve from the configured backend media base URL rather than a hard-coded path.
- Backend-owned CSP/media origins are derived from storage-media config, which keeps local and production media bases aligned with the security header policy.
- Candidate handoff status and Talent Partner submission detail now surface transcript/job status fields so failed, retrying, pending, and ready states are visible.
- The default valid Day 4 upload contract is now `video/mp4` and `.mp4` only.
- `.mov` / `video/quicktime` is rejected at upload init with `422 Unsupported contentType`, and no recording, transcript, or job rows are created for that invalid request.
- Retention and purge behavior degrades safely: purged media is hidden from playback, transcript access is removed, and the payload falls back cleanly instead of exposing broken links.

## 5. Acceptance Criteria Mapping

- Signed URL upload works: `POST /api/tasks/{task_id}/handoff/upload/init` returns a signed upload URL for valid `.mp4` input, and the upload completes through the signed PUT path.
- Correct backend base URL for playback: playback/download URLs are generated from the configured media base URL and appear in both candidate handoff status and Talent Partner submission detail payloads.
- Transcription succeeds for valid files: the transcription worker accepts valid uploaded media, reconstructs text from segments when necessary, and moves the transcript to ready when the provider returns usable transcript content.
- CSP allows local and production media: media-origin CSP coverage is derived from config and includes the local fake storage base and the configured production media endpoint.
- Retention/purge policies: retention and purge flows remove underlying media and transcript data safely, and the visible payload degrades to a purged state with no download URL.
- Failed states visible and retryable: candidate and Talent Partner payloads expose transcript/job state, including pending, failed, retryable, and ready states, so failures remain visible and can be retried.

## 6. QA

### Automated

- `poetry run pytest --no-cov tests/shared/jobs/handlers/test_shared_jobs_handlers_transcribe_recording_runtime_handler.py tests/config/test_config_storage_media_settings_utils.py tests/integrations/storage_media/test_integrations_storage_media_provider_service.py tests/shared/http/test_shared_http_security_headers_utils.py tests/media/services/test_media_storage_media_service.py` - passed.
- `poetry run pytest --no-cov tests/media/routes/test_media_handoff_upload_handoff_upload_init_success_routes.py tests/media/routes/test_media_handoff_upload_handoff_upload_init_rejects_invalid_content_type_and_size_routes.py tests/media/routes/test_media_handoff_upload_handoff_upload_end_to_end_routes.py` - passed.
- `bash precommit.sh` - passed, including repo-wide pytest and coverage gate at 96.14%.

### Manual

- Local backend started successfully.
- `POST /api/tasks/{task_id}/handoff/upload/init` returned `200` for `.mp4`.
- Signed PUT upload returned `204`.
- `POST /api/tasks/{task_id}/handoff/upload/complete` returned `200`.
- Candidate handoff status showed `pending` -> `ready` transcript progression.
- Talent Partner submission detail showed the playback URL and ready transcript.
- Purge flow resulted in a `purged` recording with `downloadUrl: null` and the transcript removed.
- Failed transcription state remained visible and retryable.
- Final contract check: `.mov` was rejected at init with `422`, and no recording, transcript, or job rows were created.

## 7. Risks / Notes

- Live invite flow hit GitHub availability issues in the local environment, so Day 4 QA setup used seeded trial/candidate data to isolate the media path.
- Ignored local `.env` / `.env.prod` overrides were used during debugging, but the shipped fix is the tracked code and test changes in this branch, not those ignored files.
- If operators explicitly override media allowlist env vars, they can widen the contract intentionally and should do so with care.

## 8. Final Outcome

This PR closes the backend slice of #294 and is ready for review.
