"""Application module for media services media privacy delete service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import repository as transcripts_repo
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    RecordingAsset,
)

logger = logging.getLogger("app.media.services.media_services_media_privacy_service")


async def delete_recording_asset(
    db: AsyncSession,
    *,
    recording_id: int,
    candidate_session: CandidateSession,
) -> RecordingAsset:
    """Delete recording asset."""
    if not settings.storage_media.MEDIA_DELETE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Media deletion is disabled"
        )

    recording = await recordings_repo.get_by_id_for_update(db, recording_id)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording asset not found"
        )
    if recording.candidate_session_id != candidate_session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this recording asset",
        )

    now = datetime.now(UTC)
    await recordings_repo.mark_deleted(db, recording=recording, now=now, commit=False)
    transcript = await transcripts_repo.get_by_recording_id(
        db, recording.id, include_deleted=True
    )
    if transcript is not None:
        await transcripts_repo.mark_deleted(
            db, transcript=transcript, now=now, commit=False
        )
    await db.commit()
    await db.refresh(recording)
    logger.info("recording deleted recordingId=%s", recording.id)
    return recording
