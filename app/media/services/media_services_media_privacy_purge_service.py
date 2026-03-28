"""Application module for media services media privacy purge service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.storage_media import StorageMediaProvider
from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_PURGED,
)
from app.media.repositories.transcripts import repository as transcripts_repo

from .media_services_media_privacy_model import MediaRetentionPurgeResult

logger = logging.getLogger("app.media.services.media_services_media_privacy_service")


async def purge_expired_media_assets(
    db: AsyncSession,
    *,
    storage_provider: StorageMediaProvider,
    retention_days: int | None = None,
    batch_limit: int = 200,
    now: datetime | None = None,
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
    failed_count = 0
    for candidate in candidates:
        try:
            recording = await recordings_repo.get_by_id_for_update(db, candidate.id)
            if (
                recording is None
                or recording.purged_at is not None
                or recording.status == RECORDING_ASSET_STATUS_PURGED
            ):
                await db.rollback()
                continue
            storage_provider.delete_object(recording.storage_key)
            await transcripts_repo.hard_delete_by_recording_id(
                db, recording.id, commit=False
            )
            await recordings_repo.mark_purged(
                db, recording=recording, now=resolved_now, commit=False
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
