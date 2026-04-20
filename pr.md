# Day 4 handoff/demo media flow: upload, transcription, duration guard, and playback

## 1. Summary

This change completes the backend for Day 4 handoff/demo media flow in Winoe AI.

- Enforces a maximum 15-minute recording duration at upload completion.
- Keeps the handoff upload init/complete flow reliable and idempotent.
- Allows preview and resubmission until the cutoff, with the latest valid recording becoming active.
- Hardens the transcription pipeline so valid uploads enqueue and complete transcript processing.
- Returns correct playback/download URLs and the expected CSP for Talent Partner playback.
- Supports supplemental materials alongside the main recording.
- Cleans up the public route contract so the canonical surface is `handoff`, not legacy `presentation`.

## 2. What Changed

### Media upload validation and completion

- Added/kept validation on handoff upload completion for content type, size, and duration.
- Enforced the 15-minute ceiling during completion so overlong uploads are rejected before they become accepted handoff media.
- Kept completion idempotent so repeated completion calls do not corrupt the recording state.

### Recording selection semantics

- Updated resubmission behavior so the latest valid recording becomes the active one for the handoff submission.
- Kept invalid or superseded attempts from replacing the active recording pointer.
- Preserved preview/resubmit behavior through the Day 4 cutoff window.

### Transcript and job behavior

- Ensured a successful completion creates the transcript record and enqueues transcription work.
- Verified the worker success path writes a ready transcript with text and segments.
- Preserved readable degraded states when transcription is pending or fails, including retry metadata.

### Candidate handoff status payloads

- Kept `/api/tasks/{task_id}/handoff/status` returning the active recording, transcript status, and supplemental materials.
- Ensured playback/download URLs are emitted when storage signing succeeds.
- Ensured storage-signing failures degrade to a null download URL instead of breaking the response.

### Talent Partner submission detail payloads

- Kept `/api/submissions/{submission_id}` returning the canonical handoff payload for Talent Partner review.
- Returned the active handoff recording, transcript, and supplemental materials in the submission detail payload.
- Returned the playback/download URL and the CSP header expected for media playback.

### OpenAPI and route contract cleanup

- Exposed the canonical `handoff` routes in OpenAPI.
- Removed public `presentation` routes from the schema so the external contract matches the canonical route naming.
- Kept route behavior aligned with the current backend vocabulary used by the handoff/demo flow.

### Tests added and updated

- Added and updated route-level tests for handoff init, complete, status, playback URL handling, CSP, transcript shapes, and supplemental materials.
- Added and updated service-level tests for upload completion, transcript job behavior, resubmission selection, and Day 4 completion gating.
- Added an OpenAPI contract test to verify the public surface exposes canonical handoff routes only.

## 3. Acceptance Criteria Mapping

- Max 15-minute duration enforced: overlong uploads are rejected with `422` at completion.
- Upload init/complete reliable: init succeeds for valid uploads, completion succeeds for valid finalized recordings, and repeated completion is safe.
- Preview and resubmit until cutoff: the backend keeps the latest valid recording active while the Day 4 window remains open.
- Transcription succeeds for valid files: valid handoff uploads create transcript work and reach the ready transcript state.
- Correct playback URLs and CSP: Talent Partner detail returns playback/download URLs, and the response includes the expected CSP for media playback.
- Supplemental materials upload: supplemental assets can be uploaded and are included in handoff/submission payloads.
- Routes renamed from `presentation` to `handoff/demo`: the canonical OpenAPI surface exposes `handoff` routes and no public `presentation` routes.

## 4. QA Evidence

- `./precommit.sh` passes on the final current branch.
- Focused automated Day 4 media/submissions tests passed, covering:
  - upload init and completion
  - 15-minute duration rejection
  - transcript creation and transcript status shaping
  - resubmission selection
  - playback/download URL behavior
  - CSP behavior
  - supplemental materials visibility
  - OpenAPI route contract cleanup
- Manual QA on the local backend/runtime proved the following outcomes:
  - overlong upload rejected with `422`
  - valid upload completes successfully
  - repeated complete is safe
  - replacement upload becomes active
  - transcript success path verified
  - degraded and missing transcript path verified
  - Talent Partner detail returns playback URL and handoff payload
  - CSP header is present and aligned to the playback origin
  - supplemental material is visible in the payload
  - OpenAPI exposes handoff routes and no public presentation routes

## 5. Local QA Caveats

- Manual QA was performed on the local backend/runtime.
- Local validation used the dev auth bypass and demo transcription mode to exercise the backend flows end to end.
- This is sufficient for backend acceptance on #290, but it is not the same as production infra validation.

## 6. Tests

- Final `./precommit.sh`
- Focused `--no-cov` Day 4 media/submissions test slice
- Targeted service tests for upload completion, transcript job behavior, and resubmission selection
- Route tests for status payloads, playback URL handling, CSP, supplemental materials, and OpenAPI route exposure

## 7. Risks / Follow-ups

None.
