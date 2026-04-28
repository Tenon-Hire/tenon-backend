"""Application module for media services media handoff upload complete service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.integrations.storage_media import StorageMediaProvider
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_KIND_RECORDING,
    RECORDING_ASSET_KIND_SUPPLEMENTAL,
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_PENDING,
)
from app.media.services.media_services_media_handoff_upload_lookup_service import (
    load_task_with_company_or_404,
)
from app.media.services.media_services_media_handoff_upload_storage_checks_service import (
    assert_uploaded_object_matches_expected,
    assert_uploaded_recording_duration_within_limit,
    load_uploaded_object_metadata,
)
from app.media.services.media_services_media_handoff_upload_submission_pointer_service import (
    upsert_submission_recording_pointer,
)
from app.media.services.media_services_media_handoff_upload_validation_service import (
    copy_candidate_consent_if_missing,
    ensure_handoff_task,
    parse_recording_id_or_422,
    require_recording_access,
)
from app.media.services.media_services_media_privacy_service import (
    compute_media_retention_expires_at,
    require_media_consent,
)
from app.media.services.media_services_media_transcription_jobs_service import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    TRANSCRIBE_RECORDING_MAX_ATTEMPTS,
    build_transcribe_recording_payload,
    transcribe_recording_idempotency_key,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    RecordingAsset,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)

logger = logging.getLogger(__name__)


async def complete_handoff_upload(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    recording_id_value: str,
    storage_provider: StorageMediaProvider,
) -> RecordingAsset:
    """Complete handoff upload."""
    task, company_id = await load_task_with_company_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    ensure_handoff_task(task.type)
    cs_service.require_active_window(candidate_session, task)
    require_media_consent(candidate_session)
    recording_id = parse_recording_id_or_422(recording_id_value)
    recording = require_recording_access(
        await recordings_repo.get_by_id_for_update(db, recording_id),
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    asset_kind = recording.asset_kind or RECORDING_ASSET_KIND_RECORDING
    copy_candidate_consent_if_missing(recording, candidate_session)
    if recording.status in {
        RECORDING_ASSET_STATUS_UPLOADING,
        RECORDING_ASSET_STATUS_FAILED,
    }:
        object_metadata = load_uploaded_object_metadata(
            storage_provider=storage_provider, storage_key=recording.storage_key
        )
        assert_uploaded_object_matches_expected(
            expected_content_type=recording.content_type,
            expected_size_bytes=recording.bytes,
            actual_content_type=object_metadata.content_type,
            actual_size_bytes=object_metadata.size_bytes,
        )
        if asset_kind == RECORDING_ASSET_KIND_RECORDING:
            assert_uploaded_recording_duration_within_limit(
                actual_duration_seconds=object_metadata.duration_seconds
            )
        recording.status = RECORDING_ASSET_STATUS_UPLOADED
    if recording.retention_expires_at is None:
        recording.retention_expires_at = compute_media_retention_expires_at(
            datetime.now(UTC)
        )
    transcript = None
    transcript_created = False
    job = None
    submission_id = None
    if asset_kind == RECORDING_ASSET_KIND_RECORDING:
        (
            transcript,
            transcript_created,
        ) = await transcripts_repo.get_or_create_transcript(
            db,
            recording_id=recording.id,
            status=TRANSCRIPT_STATUS_PENDING,
            commit=False,
        )
        submission_id = await upsert_submission_recording_pointer(
            db,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            recording_id=recording.id,
            submitted_at=datetime.now(UTC),
        )
        job = await jobs_repo.create_or_get_idempotent(
            db,
            job_type=TRANSCRIBE_RECORDING_JOB_TYPE,
            idempotency_key=transcribe_recording_idempotency_key(recording.id),
            payload_json=build_transcribe_recording_payload(
                recording_id=recording.id,
                candidate_session_id=candidate_session.id,
                task_id=task.id,
                company_id=company_id,
            ),
            company_id=company_id,
            candidate_session_id=candidate_session.id,
            max_attempts=TRANSCRIBE_RECORDING_MAX_ATTEMPTS,
            correlation_id=f"recording:{recording.id}",
            commit=False,
        )
    elif asset_kind != RECORDING_ASSET_KIND_SUPPLEMENTAL:
        raise AssertionError(f"Unsupported recording asset kind: {asset_kind}")
    await db.commit()
    logger.info(
        "Recording upload completed recordingId=%s candidateSessionId=%s taskId=%s status=%s",
        recording.id,
        candidate_session.id,
        task.id,
        recording.status,
    )
    if transcript_created and transcript is not None:
        logger.info(
            "Transcript placeholder created recordingId=%s transcriptId=%s status=%s",
            recording.id,
            transcript.id,
            transcript.status,
        )
    if submission_id is not None:
        logger.info(
            "Handoff submission recording pointer updated submissionId=%s taskId=%s recordingId=%s",
            submission_id,
            task.id,
            recording.id,
        )
    if job is not None:
        logger.info(
            "Transcription job ensured recordingId=%s jobId=%s jobType=%s",
            recording.id,
            job.id,
            TRANSCRIBE_RECORDING_JOB_TYPE,
        )
    return recording


__all__ = ["complete_handoff_upload"]
