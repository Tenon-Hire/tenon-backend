"""Application module for tasks routes tasks handoff upload status handler workflows."""

from __future__ import annotations

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    HandoffStatusResponse,
)


async def handoff_status_route_impl(
    *,
    task_id: int,
    candidate_session,
    db,
    storage_provider,
    get_handoff_status_fn,
    is_downloadable_fn,
    resolve_signed_url_ttl_fn,
    recording_public_id_fn,
    build_transcript_status_payload_fn,
    logger,
) -> HandoffStatusResponse:
    """Execute handoff status route impl."""
    recording, transcript = await get_handoff_status_fn(
        db,
        candidate_session=candidate_session,
        task_id=task_id,
    )
    recording_payload = None
    if recording is not None:
        download_url = None
        if is_downloadable_fn(recording):
            try:
                download_url = storage_provider.create_signed_download_url(
                    recording.storage_key,
                    expires_seconds=resolve_signed_url_ttl_fn(),
                )
            except (StorageMediaError, ValueError) as exc:
                logger.warning(
                    "Failed to sign candidate handoff status download URL recordingId=%s taskId=%s candidateSessionId=%s",
                    recording.id,
                    task_id,
                    candidate_session.id,
                    exc_info=exc,
                )
        recording_payload = {
            "recordingId": recording_public_id_fn(recording.id),
            "status": recording.status,
            "downloadUrl": download_url,
        }

    transcript_payload = None
    if transcript is not None:
        transcript_payload = build_transcript_status_payload_fn(transcript)
    return HandoffStatusResponse(
        recording=recording_payload, transcript=transcript_payload
    )
