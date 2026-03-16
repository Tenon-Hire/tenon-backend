from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.domains import CandidateSession, RecordingAsset
from app.integrations.storage_media import StorageMediaProvider
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import RECORDING_ASSET_STATUS_PURGED
from app.repositories.transcripts import repository as transcripts_repo

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MediaRetentionPurgeResult:
    scanned_count: int
    purged_count: int
    failed_count: int
    purged_recording_ids: list[int]


def _normalized_notice_version(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="noticeVersion is required",
        )
    return normalized


def require_media_consent(candidate_session: CandidateSession) -> None:
    if not (candidate_session.consent_version or "").strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent is required before upload completion",
        )
    if candidate_session.consent_timestamp is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent is required before upload completion",
        )


async def record_candidate_session_consent(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    notice_version: str,
    ai_notice_version: str | None = None,
) -> CandidateSession:
    resolved_notice_version = _normalized_notice_version(notice_version)
    resolved_ai_notice_version = (
        (ai_notice_version or "").strip()
        or (getattr(candidate_session, "ai_notice_version", "") or "").strip()
        or resolved_notice_version
    )

    if (
        candidate_session.consent_version == resolved_notice_version
        and candidate_session.ai_notice_version == resolved_ai_notice_version
        and candidate_session.consent_timestamp is not None
    ):
        logger.info(
            "consent recorded candidateSessionId=%s consentVersion=%s consentTimestamp=%s",
            candidate_session.id,
            candidate_session.consent_version,
            candidate_session.consent_timestamp.isoformat()
            if candidate_session.consent_timestamp is not None
            else None,
        )
        return candidate_session

    now = datetime.now(UTC)
    candidate_session.consent_version = resolved_notice_version
    candidate_session.consent_timestamp = now
    candidate_session.ai_notice_version = resolved_ai_notice_version
    await db.commit()
    await db.refresh(candidate_session)

    logger.info(
        "consent recorded candidateSessionId=%s consentVersion=%s consentTimestamp=%s",
        candidate_session.id,
        candidate_session.consent_version,
        candidate_session.consent_timestamp.isoformat()
        if candidate_session.consent_timestamp is not None
        else None,
    )
    return candidate_session


async def delete_recording_asset(
    db: AsyncSession,
    *,
    recording_id: int,
    candidate_session: CandidateSession,
) -> RecordingAsset:
    if not settings.storage_media.MEDIA_DELETE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Media deletion is disabled",
        )

    recording = await recordings_repo.get_by_id_for_update(db, recording_id)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording asset not found",
        )
    if recording.candidate_session_id != candidate_session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this recording asset",
        )

    now = datetime.now(UTC)
    await recordings_repo.mark_deleted(
        db,
        recording=recording,
        now=now,
        commit=False,
    )

    transcript = await transcripts_repo.get_by_recording_id(
        db,
        recording.id,
        include_deleted=True,
    )
    if transcript is not None:
        await transcripts_repo.mark_deleted(
            db,
            transcript=transcript,
            now=now,
            commit=False,
        )

    await db.commit()
    await db.refresh(recording)
    logger.info("recording deleted recordingId=%s", recording.id)
    return recording


async def purge_expired_media_assets(
    db: AsyncSession,
    *,
    storage_provider: StorageMediaProvider,
    retention_days: int | None = None,
    batch_limit: int = 200,
    now: datetime | None = None,
) -> MediaRetentionPurgeResult:
    resolved_now = now or datetime.now(UTC)
    resolved_retention_days = int(
        retention_days
        if retention_days is not None
        else settings.storage_media.MEDIA_RETENTION_DAYS
    )

    candidates = await recordings_repo.get_expired_for_retention(
        db,
        retention_days=resolved_retention_days,
        now=resolved_now,
        limit=batch_limit,
    )

    purged_recording_ids: list[int] = []
    failed_count = 0

    for candidate in candidates:
        try:
            recording = await recordings_repo.get_by_id_for_update(db, candidate.id)
            if recording is None:
                await db.rollback()
                continue
            if (
                recording.purged_at is not None
                or recording.status == RECORDING_ASSET_STATUS_PURGED
            ):
                await db.rollback()
                continue

            storage_provider.delete_object(recording.storage_key)
            await transcripts_repo.hard_delete_by_recording_id(
                db,
                recording.id,
                commit=False,
            )
            await recordings_repo.mark_purged(
                db,
                recording=recording,
                now=resolved_now,
                commit=False,
            )
            await db.commit()
            purged_recording_ids.append(recording.id)
            logger.info("purge executed recordingId=%s", recording.id)
        except StorageMediaError as exc:
            await db.rollback()
            failed_count += 1
            logger.warning(
                "purge failed recordingId=%s reason=%s",
                candidate.id,
                " ".join(str(exc).split())[:255],
            )
        except Exception:
            await db.rollback()
            failed_count += 1
            logger.exception("purge failed recordingId=%s", candidate.id)

    return MediaRetentionPurgeResult(
        scanned_count=len(candidates),
        purged_count=len(purged_recording_ids),
        failed_count=failed_count,
        purged_recording_ids=purged_recording_ids,
    )


__all__ = [
    "MediaRetentionPurgeResult",
    "delete_recording_asset",
    "purge_expired_media_assets",
    "record_candidate_session_consent",
    "require_media_consent",
]
