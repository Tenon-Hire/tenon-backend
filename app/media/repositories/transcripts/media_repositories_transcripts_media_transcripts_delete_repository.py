"""Application module for media repositories transcripts media transcripts delete repository workflows."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    Transcript,
)


async def hard_delete_by_recording_id(
    db: AsyncSession,
    recording_id: int,
    *,
    commit: bool = True,
) -> int:
    """Execute hard delete by recording id."""
    result = await db.execute(
        delete(Transcript).where(Transcript.recording_id == recording_id)
    )
    deleted_count = int(result.rowcount or 0)
    if commit:
        await db.commit()
    return deleted_count
