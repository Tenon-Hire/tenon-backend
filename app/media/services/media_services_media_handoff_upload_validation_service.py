"""Application module for media services media handoff upload validation service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.media.services.media_services_media_keys_service import (
    parse_recording_public_id,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    RecordingAsset,
)


def ensure_handoff_task(task_type: str) -> None:
    """Ensure handoff task."""
    if (task_type or "").lower() != "handoff":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Media upload is only supported for handoff tasks",
        )


def parse_recording_id_or_422(recording_id_value: str) -> int:
    """Parse recording id or 422."""
    try:
        return parse_recording_public_id(recording_id_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def require_recording_access(
    recording: RecordingAsset | None, *, candidate_session_id: int, task_id: int
) -> RecordingAsset:
    """Require recording access."""
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording asset not found",
        )
    if (
        recording.candidate_session_id != candidate_session_id
        or recording.task_id != task_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this recording asset",
        )
    return recording


def copy_candidate_consent_if_missing(
    recording: RecordingAsset,
    candidate_session: CandidateSession,
) -> None:
    """Execute copy candidate consent if missing."""
    if (
        recording.consent_timestamp is not None
        or candidate_session.consent_timestamp is None
    ):
        return
    recording.consent_version = candidate_session.consent_version
    recording.consent_timestamp = candidate_session.consent_timestamp
    recording.ai_notice_version = candidate_session.ai_notice_version


__all__ = [
    "copy_candidate_consent_if_missing",
    "ensure_handoff_task",
    "parse_recording_id_or_422",
    "require_recording_access",
]
