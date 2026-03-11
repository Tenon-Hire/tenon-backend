from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession
from app.domains.candidate_sessions import service as cs_service
from app.domains.submissions import service_candidate as submission_service
from app.integrations.storage_media import StorageMediaProvider, resolve_signed_url_ttl
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
    RecordingAsset,
)
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_PENDING
from app.services.media.keys import (
    build_recording_storage_key,
    parse_recording_public_id,
)
from app.services.media.validation import UploadInput, validate_upload_input

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
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    _ensure_handoff_task(task.type)
    cs_service.require_active_window(candidate_session, task)

    validated: UploadInput = validate_upload_input(
        content_type=content_type,
        size_bytes=size_bytes,
        filename=filename,
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media storage unavailable",
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


async def complete_handoff_upload(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    recording_id_value: str,
    storage_provider: StorageMediaProvider,
) -> RecordingAsset:
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    _ensure_handoff_task(task.type)
    cs_service.require_active_window(candidate_session, task)

    try:
        recording_id = parse_recording_public_id(recording_id_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    recording = await recordings_repo.get_by_id_for_update(db, recording_id)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording asset not found",
        )
    if (
        recording.candidate_session_id != candidate_session.id
        or recording.task_id != task.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this recording asset",
        )

    changed = False
    if recording.status in {
        RECORDING_ASSET_STATUS_UPLOADING,
        RECORDING_ASSET_STATUS_FAILED,
    }:
        object_metadata = _load_uploaded_object_metadata(
            storage_provider=storage_provider,
            storage_key=recording.storage_key,
        )
        _assert_uploaded_object_matches_expected(
            expected_content_type=recording.content_type,
            expected_size_bytes=recording.bytes,
            actual_content_type=object_metadata.content_type,
            actual_size_bytes=object_metadata.size_bytes,
        )
        recording.status = RECORDING_ASSET_STATUS_UPLOADED
        changed = True

    transcript, transcript_created = await transcripts_repo.get_or_create_transcript(
        db,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_PENDING,
        commit=False,
    )
    if changed or transcript_created:
        await db.commit()
        await db.refresh(recording)
        await db.refresh(transcript)

    logger.info(
        "Recording upload completed recordingId=%s candidateSessionId=%s taskId=%s status=%s",
        recording.id,
        candidate_session.id,
        task.id,
        recording.status,
    )
    if transcript_created:
        logger.info(
            "Transcript placeholder created recordingId=%s transcriptId=%s status=%s",
            recording.id,
            transcript.id,
            transcript.status,
        )
    return recording


def _ensure_handoff_task(task_type: str) -> None:
    if (task_type or "").lower() != "handoff":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Media upload is only supported for handoff tasks",
        )


def _load_uploaded_object_metadata(
    *,
    storage_provider: StorageMediaProvider,
    storage_key: str,
):
    try:
        metadata = storage_provider.get_object_metadata(storage_key)
    except StorageMediaError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media storage unavailable",
        ) from exc
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded object not found",
        )
    return metadata


def _assert_uploaded_object_matches_expected(
    *,
    expected_content_type: str,
    expected_size_bytes: int,
    actual_content_type: str,
    actual_size_bytes: int,
) -> None:
    if int(actual_size_bytes) != int(expected_size_bytes):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded object size does not match expected size",
        )
    expected_type = _normalize_content_type(expected_content_type)
    actual_type = _normalize_content_type(actual_content_type)
    if actual_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded object content type does not match expected contentType",
        )


def _normalize_content_type(value: str) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


__all__ = ["complete_handoff_upload", "init_handoff_upload"]
