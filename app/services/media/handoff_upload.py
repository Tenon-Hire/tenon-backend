from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import MEDIA_STORAGE_UNAVAILABLE, REQUEST_TOO_LARGE, ApiError
from app.core.settings import settings
from app.domains import CandidateSession, RecordingAsset, Simulation, Transcript
from app.domains.candidate_sessions import service as cs_service
from app.domains.submissions import service_candidate as submission_service
from app.integrations.storage_media import StorageMediaProvider, resolve_signed_url_ttl
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.jobs import repository as jobs_repo
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
)
from app.repositories.submissions import repository as submissions_repo
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_PENDING
from app.services.media.keys import (
    build_recording_storage_key,
    parse_recording_public_id,
)
from app.services.media.transcription_jobs import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    TRANSCRIBE_RECORDING_MAX_ATTEMPTS,
    build_transcribe_recording_payload,
    transcribe_recording_idempotency_key,
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

    transcript, transcript_created = await transcripts_repo.get_or_create_transcript(
        db,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_PENDING,
        commit=False,
    )

    now = datetime.now(UTC)
    submission, submission_changed = await _upsert_submission_recording_pointer(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        recording_id=recording.id,
        submitted_at=now,
    )

    company_id = await _resolve_company_id(
        db,
        candidate_session=candidate_session,
        simulation_id=task.simulation_id,
    )
    job = await jobs_repo.create_or_get_idempotent(
        db,
        job_type=TRANSCRIBE_RECORDING_JOB_TYPE,
        idempotency_key=transcribe_recording_idempotency_key(recording.id),
        payload_json=build_transcribe_recording_payload(
            recording_id=recording.id,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
        ),
        company_id=company_id,
        candidate_session_id=candidate_session.id,
        max_attempts=TRANSCRIBE_RECORDING_MAX_ATTEMPTS,
        correlation_id=f"recording:{recording.id}",
        commit=False,
    )

    await db.commit()
    await db.refresh(recording)

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
    if submission_changed:
        logger.info(
            "Handoff submission recording pointer updated submissionId=%s taskId=%s recordingId=%s",
            submission.id,
            task.id,
            recording.id,
        )
    logger.info(
        "Transcription job ensured recordingId=%s jobId=%s jobType=%s",
        recording.id,
        job.id,
        TRANSCRIBE_RECORDING_JOB_TYPE,
    )
    return recording


async def get_handoff_status(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
) -> tuple[RecordingAsset | None, Transcript | None]:
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    _ensure_handoff_task(task.type)

    recording = await recordings_repo.get_latest_for_task_session(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )

    transcript: Transcript | None = None
    if recording is not None:
        transcript = await transcripts_repo.get_by_recording_id(db, recording.id)

    return recording, transcript


async def _upsert_submission_recording_pointer(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    recording_id: int,
    submitted_at: datetime,
):
    existing = await submissions_repo.get_by_candidate_session_task(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        for_update=True,
    )
    if existing is not None:
        changed = False
        if existing.recording_id != recording_id:
            existing.recording_id = recording_id
            existing.submitted_at = submitted_at
            changed = True
        if changed:
            await db.flush()
        return existing, changed

    try:
        async with db.begin_nested():
            created = await submissions_repo.create_handoff_submission(
                db,
                candidate_session_id=candidate_session_id,
                task_id=task_id,
                recording_id=recording_id,
                submitted_at=submitted_at,
                commit=False,
            )
        return created, True
    except IntegrityError:
        fallback = await submissions_repo.get_by_candidate_session_task(
            db,
            candidate_session_id=candidate_session_id,
            task_id=task_id,
            for_update=True,
        )
        if fallback is None:
            raise
        changed = fallback.recording_id != recording_id
        if changed:
            fallback.recording_id = recording_id
            fallback.submitted_at = submitted_at
            await db.flush()
        return fallback, changed


async def _resolve_company_id(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    simulation_id: int,
) -> int:
    simulation = candidate_session.__dict__.get("simulation")
    if simulation is not None and isinstance(
        getattr(simulation, "company_id", None), int
    ):
        return simulation.company_id

    company_id = (
        await db.execute(
            select(Simulation.company_id).where(Simulation.id == simulation_id)
        )
    ).scalar_one_or_none()
    if not isinstance(company_id, int):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation metadata unavailable",
        )
    return company_id


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
        raise ApiError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Media storage unavailable",
            error_code=MEDIA_STORAGE_UNAVAILABLE,
            retryable=True,
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
    actual_size = int(actual_size_bytes)
    expected_size = int(expected_size_bytes)
    max_bytes = int(settings.storage_media.MEDIA_MAX_UPLOAD_BYTES)

    if actual_size > max_bytes:
        raise ApiError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded object size exceeds max {max_bytes}",
            error_code=REQUEST_TOO_LARGE,
            retryable=False,
            details={
                "field": "sizeBytes",
                "maxBytes": max_bytes,
                "actualBytes": actual_size,
            },
        )

    if actual_size != expected_size:
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


__all__ = ["complete_handoff_upload", "get_handoff_status", "init_handoff_upload"]
