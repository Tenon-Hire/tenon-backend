"""Application module for media services media privacy purge service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories.candidates_candidate_sessions_repositories_candidates_candidate_sessions_candidate_session_model import (
    CandidateSession,
)
from app.config import settings
from app.integrations.storage_media import StorageMediaProvider
from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.media.repositories.purge_audits import (
    MEDIA_PURGE_ACTOR_OPERATOR,
    MEDIA_PURGE_ACTOR_SYSTEM,
    MEDIA_PURGE_OUTCOME_FAILED,
    MEDIA_PURGE_OUTCOME_SKIPPED,
    MEDIA_PURGE_OUTCOME_SUCCESS,
)
from app.media.repositories.purge_audits import (
    create_audit as create_purge_audit,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_PURGE_REASON_DATA_REQUEST,
    RECORDING_ASSET_PURGE_REASON_RETENTION_EXPIRED,
    RECORDING_ASSET_PURGE_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PURGED,
    RecordingAsset,
)
from app.media.repositories.transcripts import repository as transcripts_repo

from .media_services_media_privacy_model import MediaRetentionPurgeResult

logger = logging.getLogger("app.media.services.media_services_media_privacy_service")

_SAFE_ERROR_MAX_LENGTH = 255


def compute_media_retention_expires_at(
    anchor: datetime | None = None, *, retention_days: int | None = None
) -> datetime:
    """Return the expiration timestamp for a media retention policy."""
    resolved_anchor = anchor or datetime.now(UTC)
    resolved_days = int(retention_days or settings.storage_media.MEDIA_RETENTION_DAYS)
    if resolved_days <= 0:
        raise ValueError("MEDIA_RETENTION_DAYS must be > 0")
    return resolved_anchor + timedelta(days=resolved_days)


def _safe_error_summary(exc: Exception) -> str:
    return " ".join(str(exc).split())[:_SAFE_ERROR_MAX_LENGTH]


async def _candidate_context(
    db: AsyncSession, candidate_session_id: int | None
) -> tuple[int | None, int | None]:
    if candidate_session_id is None:
        return None, None
    candidate_session = await db.get(CandidateSession, candidate_session_id)
    if candidate_session is None:
        return None, None
    return candidate_session.trial_id, candidate_session.candidate_user_id


async def _write_audit(
    db: AsyncSession,
    *,
    recording: RecordingAsset,
    actor_type: str,
    actor_id: str | None,
    purge_reason: str,
    outcome: str,
    error_summary: str | None = None,
) -> None:
    candidate_session_id = getattr(recording, "candidate_session_id", None)
    trial_id, candidate_user_id = await _candidate_context(db, candidate_session_id)
    await create_purge_audit(
        db,
        media_id=recording.id,
        candidate_session_id=candidate_session_id,
        trial_id=trial_id,
        candidate_user_id=candidate_user_id,
        actor_type=actor_type,
        actor_id=actor_id,
        purge_reason=purge_reason,
        outcome=outcome,
        error_summary=error_summary,
        commit=False,
    )


async def _purge_recording(
    db: AsyncSession,
    *,
    recording_id: int,
    storage_provider: StorageMediaProvider,
    purge_reason: str,
    actor_type: str,
    actor_id: str | None,
    now: datetime,
) -> tuple[bool, bool]:
    recording = await recordings_repo.get_by_id_for_update(db, recording_id)
    if recording is None:
        return False, True
    if (
        recording.purged_at is not None
        or recording.status == RECORDING_ASSET_STATUS_PURGED
    ):
        await _write_audit(
            db,
            recording=recording,
            actor_type=actor_type,
            actor_id=actor_id,
            purge_reason=purge_reason,
            outcome=MEDIA_PURGE_OUTCOME_SKIPPED,
        )
        await db.commit()
        return False, True
    try:
        storage_provider.delete_object(recording.storage_key)
        if (
            purge_reason == RECORDING_ASSET_PURGE_REASON_RETENTION_EXPIRED
            and recording.retention_expires_at is None
        ):
            recording.retention_expires_at = now
        await transcripts_repo.redact_by_recording_id(
            db, recording.id, now=now, commit=False
        )
        await recordings_repo.mark_purged(
            db,
            recording=recording,
            purge_reason=purge_reason,
            now=now,
            commit=False,
        )
        await _write_audit(
            db,
            recording=recording,
            actor_type=actor_type,
            actor_id=actor_id,
            purge_reason=purge_reason,
            outcome=MEDIA_PURGE_OUTCOME_SUCCESS,
        )
        await db.commit()
        logger.info(
            "media_purge_event outcome=success mediaId=%s reason=%s",
            recording.id,
            purge_reason,
        )
        return True, False
    except StorageMediaError as exc:
        await db.rollback()
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is not None:
            recording.purge_reason = purge_reason
            recording.purge_status = RECORDING_ASSET_PURGE_STATUS_FAILED
            error_summary = _safe_error_summary(exc)
            await _write_audit(
                db,
                recording=recording,
                actor_type=actor_type,
                actor_id=actor_id,
                purge_reason=purge_reason,
                outcome=MEDIA_PURGE_OUTCOME_FAILED,
                error_summary=error_summary,
            )
            await db.commit()
        logger.warning(
            "media_purge_event outcome=failed mediaId=%s reason=%s error=%s",
            recording_id,
            purge_reason,
            _safe_error_summary(exc),
        )
        return False, False
    except Exception as exc:
        await db.rollback()
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is not None:
            recording.purge_reason = purge_reason
            recording.purge_status = RECORDING_ASSET_PURGE_STATUS_FAILED
            await _write_audit(
                db,
                recording=recording,
                actor_type=actor_type,
                actor_id=actor_id,
                purge_reason=purge_reason,
                outcome=MEDIA_PURGE_OUTCOME_FAILED,
                error_summary=type(exc).__name__,
            )
            await db.commit()
        logger.warning(
            "media_purge_event outcome=failed mediaId=%s reason=%s errorType=%s",
            recording_id,
            purge_reason,
            type(exc).__name__,
        )
        return False, False


async def purge_expired_media_assets(
    db: AsyncSession,
    *,
    storage_provider: StorageMediaProvider,
    retention_days: int | None = None,
    batch_limit: int = 200,
    now: datetime | None = None,
    actor_type: str = MEDIA_PURGE_ACTOR_SYSTEM,
    actor_id: str | None = None,
) -> MediaRetentionPurgeResult:
    """Purge expired media assets."""
    resolved_now = now or datetime.now(UTC)
    resolved_retention_days = int(
        retention_days or settings.storage_media.MEDIA_RETENTION_DAYS
    )
    candidates = await recordings_repo.get_expired_for_retention(
        db,
        retention_days=resolved_retention_days,
        now=resolved_now,
        limit=batch_limit,
    )

    purged_recording_ids: list[int] = []
    skipped_count = 0
    failed_count = 0
    for candidate in candidates:
        purged, skipped = await _purge_recording(
            db,
            recording_id=candidate.id,
            storage_provider=storage_provider,
            purge_reason=RECORDING_ASSET_PURGE_REASON_RETENTION_EXPIRED,
            actor_type=actor_type,
            actor_id=actor_id,
            now=resolved_now,
        )
        if purged:
            purged_recording_ids.append(candidate.id)
        elif skipped:
            skipped_count += 1
        else:
            failed_count += 1

    return MediaRetentionPurgeResult(
        scanned_count=len(candidates),
        purged_count=len(purged_recording_ids),
        skipped_count=skipped_count,
        failed_count=failed_count,
        purged_recording_ids=purged_recording_ids,
    )


async def purge_candidate_session_media_for_data_request(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    storage_provider: StorageMediaProvider,
    actor_type: str = MEDIA_PURGE_ACTOR_OPERATOR,
    actor_id: str | None = None,
    batch_limit: int = 500,
    now: datetime | None = None,
) -> MediaRetentionPurgeResult:
    """Purge media for a Candidate data deletion request."""
    resolved_now = now or datetime.now(UTC)
    recordings = await recordings_repo.list_for_candidate_session(
        db,
        candidate_session_id=candidate_session_id,
        include_purged=False,
        limit=batch_limit,
    )
    purged_recording_ids: list[int] = []
    skipped_count = 0
    failed_count = 0
    for recording in recordings:
        purged, skipped = await _purge_recording(
            db,
            recording_id=recording.id,
            storage_provider=storage_provider,
            purge_reason=RECORDING_ASSET_PURGE_REASON_DATA_REQUEST,
            actor_type=actor_type,
            actor_id=actor_id,
            now=resolved_now,
        )
        if purged:
            purged_recording_ids.append(recording.id)
        elif skipped:
            skipped_count += 1
        else:
            failed_count += 1

    return MediaRetentionPurgeResult(
        scanned_count=len(recordings),
        purged_count=len(purged_recording_ids),
        skipped_count=skipped_count,
        failed_count=failed_count,
        purged_recording_ids=purged_recording_ids,
    )


__all__ = [
    "compute_media_retention_expires_at",
    "purge_candidate_session_media_for_data_request",
    "purge_expired_media_assets",
]
