"""Application module for media repositories transcripts media transcripts delete repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
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


async def redact_by_recording_id(
    db: AsyncSession,
    recording_id: int,
    *,
    now: datetime | None = None,
    commit: bool = True,
) -> int:
    """Redact transcript content for a purged recording while keeping audit shape."""
    existing = (
        await db.execute(
            select(Transcript).where(Transcript.recording_id == recording_id)
        )
    ).scalar_one_or_none()
    if existing is None:
        return 0
    resolved_now = now or datetime.now(UTC)
    existing.text = None
    existing.segments_json = None
    existing.last_error = None
    if existing.deleted_at is None:
        existing.deleted_at = resolved_now
    if commit:
        await db.commit()
        await db.refresh(existing)
    else:
        await db.flush()
    return 1
