"""Application module for media repositories transcripts media transcripts lookup repository workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    Transcript,
)


async def get_by_recording_id(
    db: AsyncSession,
    recording_id: int,
    *,
    include_deleted: bool = False,
) -> Transcript | None:
    """Return by recording id."""
    stmt = select(Transcript).where(Transcript.recording_id == recording_id)
    if not include_deleted:
        stmt = stmt.where(Transcript.deleted_at.is_(None))
    return (await db.execute(stmt)).scalar_one_or_none()
