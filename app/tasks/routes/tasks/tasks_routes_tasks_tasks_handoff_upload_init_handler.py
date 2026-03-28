"""Application module for tasks routes tasks handoff upload init handler workflows."""

from __future__ import annotations

from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    HandoffUploadInitResponse,
)


async def init_handoff_upload_route_impl(
    *,
    task_id: int,
    payload,
    candidate_session,
    db,
    storage_provider,
    init_handoff_upload_fn,
    recording_public_id_fn,
) -> HandoffUploadInitResponse:
    """Initialize handoff upload route impl."""
    recording, upload_url, expires_seconds = await init_handoff_upload_fn(
        db,
        candidate_session=candidate_session,
        task_id=task_id,
        content_type=payload.contentType,
        size_bytes=payload.sizeBytes,
        filename=payload.filename,
        storage_provider=storage_provider,
    )
    return HandoffUploadInitResponse(
        recordingId=recording_public_id_fn(recording.id),
        uploadUrl=upload_url,
        expiresInSeconds=expires_seconds,
    )
