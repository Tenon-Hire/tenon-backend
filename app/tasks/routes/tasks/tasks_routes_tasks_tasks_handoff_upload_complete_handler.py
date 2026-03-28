"""Application module for tasks routes tasks handoff upload complete handler workflows."""

from __future__ import annotations

from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    HandoffUploadCompleteResponse,
)


async def complete_handoff_upload_route_impl(
    *,
    task_id: int,
    payload,
    candidate_session,
    db,
    storage_provider,
    complete_handoff_upload_fn,
    recording_public_id_fn,
) -> HandoffUploadCompleteResponse:
    """Complete handoff upload route impl."""
    recording = await complete_handoff_upload_fn(
        db,
        candidate_session=candidate_session,
        task_id=task_id,
        recording_id_value=payload.recordingId,
        storage_provider=storage_provider,
    )
    return HandoffUploadCompleteResponse(
        recordingId=recording_public_id_fn(recording.id),
        status=recording.status,
    )
