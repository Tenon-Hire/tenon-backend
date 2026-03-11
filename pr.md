# Issue #211 Patch 2: Added `_handoff_revisit_task(...)` in progress service to override computed current task

## Title
Extend candidate handoff status payload with preview URL and ready transcript content/segments

## TL;DR
- Extended existing candidate `GET /api/tasks/{task_id}/handoff/status` response (no new endpoint) to include richer media/transcript contract.
- Added signed candidate preview URL via `recording.downloadUrl` when the latest attempt is downloadable.
- Added transcript `text` and typed timestamped `segments` when transcript status is `ready`.
- If candidate URL signing fails, the endpoint now degrades gracefully with `downloadUrl: null` and warning logging.

## Problem
Candidate handoff status previously surfaced processing metadata only (recording/transcript status), but not the persisted preview URL or ready transcript content needed by frontend Day 4 flow. Frontend Issue #140 required candidate revisit/reload preview plus transcript rendering with timestamped segments. Without this contract extension, Day 4 candidate revisit UX could not fully render prior evidence state.

## What changed
- Extended the existing candidate status endpoint; no new endpoint was introduced.
- Candidate status payload now includes:
  - `recording.downloadUrl`
  - `transcript.text`
  - `transcript.segments`
- Transcript segments are now returned through a typed response schema (`HandoffStatusTranscriptSegmentOut`).
- Added segment normalization/coercion for compatibility-safe serialization (drops invalid items, normalizes ids/timestamps).
- URL signing failures now gracefully degrade to `downloadUrl: null` with warning logging instead of failing status polling.
- Preserved latest-attempt semantics for candidate status resolution (status reflects most recent handoff attempt).
- Preserved read-after-cutoff behavior for candidate status polling.
- Upload init/complete behavior remains unchanged by this follow-up.

## API / contract notes
Candidate status response shape:

```json
{
  "recording": {
    "recordingId": "rec_123",
    "status": "uploaded",
    "downloadUrl": "https://..."
  },
  "transcript": {
    "status": "ready",
    "progress": null,
    "text": "full transcript text",
    "segments": [
      {
        "id": null,
        "startMs": 0,
        "endMs": 1250,
        "text": "hello"
      }
    ]
  }
}
```

- `downloadUrl` may be `null` if signing temporarily fails.
- `text` and `segments` are populated only when transcript status is `ready`.
- Contract remains candidate-owner scoped.

## Security / behavior notes
- Candidate auth path is unchanged.
- Candidate can access only their own handoff recording/transcript state.
- Signed URLs remain short-lived.
- No recruiter-only fields are exposed in candidate status.
- Read access after cutoff remains available; write gating (init/complete) is unchanged.

## Testing
- Targeted API tests for candidate handoff status passed.
- Targeted router/unit tests passed.
- Service tests passed, including integrity-race fallback coverage.
- Recruiter submission detail regression tests passed where touched.
- Full `poetry run pytest -q` passed with coverage enforcement.
- `./precommit.sh` passed.

Final gate:
- Exit code: `0`
- Coverage: `99.01%`

## Risks / follow-ups
- Persisted preview depends on short-lived signed URLs.
- `downloadUrl` may degrade to `null` on transient signing failures.
- Transcript segment `id` is optional and may be `null`.

## Frontend dependency note
This backend follow-up unblocks frontend Issue #140 by providing candidate-facing status fields required for:
- persisted preview on revisit/reload
- transcript text rendering
- timestamped segment rendering
