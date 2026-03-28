"""Application module for media services media handoff upload init service workflows."""

from __future__ import annotations

import logging

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.integrations.storage_media import StorageMediaProvider, resolve_signed_url_ttl
from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_UPLOADING,
)
from app.media.services.media_services_media_handoff_upload_validation_service import (
    ensure_handoff_task,
)
from app.media.services.media_services_media_keys_service import (
    build_recording_storage_key,
)
from app.media.services.media_services_media_validation_service import (
    UploadInput,
    validate_upload_input,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    RecordingAsset,
)
from app.shared.utils.shared_utils_errors_utils import (
    MEDIA_STORAGE_UNAVAILABLE,
    ApiError,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)

logger = logging.getLogger(__name__)


async def init_handoff_upload(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    content_type: str,
    size_bytes: int,
    filename: str | None,
    storage_provider: StorageMediaProvider,
) -> tuple[RecordingAsset, str, int]:
    """Initialize handoff upload."""
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    ensure_handoff_task(task.type)
    cs_service.require_active_window(candidate_session, task)
    validated: UploadInput = validate_upload_input(
        content_type=content_type, size_bytes=size_bytes, filename=filename
    )
    storage_key = build_recording_storage_key(
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        extension=validated.extension,
    )
    expires_seconds = resolve_signed_url_ttl()
    recording = await recordings_repo.create_recording_asset(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=storage_key,
        content_type=validated.content_type,
        bytes_count=validated.size_bytes,
        status=RECORDING_ASSET_STATUS_UPLOADING,
        commit=False,
    )
    try:
        upload_url = storage_provider.create_signed_upload_url(
            key=storage_key,
            content_type=validated.content_type,
            size_bytes=validated.size_bytes,
            expires_seconds=expires_seconds,
        )
    except StorageMediaError as exc:
        await db.rollback()
        raise ApiError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Media storage unavailable",
            error_code=MEDIA_STORAGE_UNAVAILABLE,
            retryable=True,
        ) from exc
    await db.commit()
    await db.refresh(recording)
    logger.info(
        "Recording asset created recordingId=%s candidateSessionId=%s taskId=%s",
        recording.id,
        candidate_session.id,
        task.id,
    )
    return recording, upload_url, expires_seconds


__all__ = ["init_handoff_upload"]
