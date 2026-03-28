"""Application module for media repositories transcripts media transcripts create repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    Transcript,
)

from .media_repositories_transcripts_media_transcripts_lookup_repository import (
    get_by_recording_id,
)


async def create_transcript(
    db: AsyncSession,
    *,
    recording_id: int,
    status: str,
    text: str | None = None,
    segments_json: list[dict[str, Any]] | None = None,
    model_name: str | None = None,
    last_error: str | None = None,
    created_at: datetime | None = None,
    commit: bool = True,
) -> Transcript:
    """Create transcript."""
    transcript = Transcript(
        recording_id=recording_id,
        status=status,
        text=text,
        segments_json=segments_json,
        model_name=model_name,
        last_error=last_error,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(transcript)
    if commit:
        await db.commit()
        await db.refresh(transcript)
    else:
        await db.flush()
    return transcript


async def get_or_create_transcript(
    db: AsyncSession,
    *,
    recording_id: int,
    status: str,
    commit: bool = True,
) -> tuple[Transcript, bool]:
    """Return or create transcript."""
    if not commit:
        try:
            async with db.begin_nested():
                created = await create_transcript(
                    db, recording_id=recording_id, status=status, commit=False
                )
            return created, True
        except IntegrityError:
            existing = await get_by_recording_id(db, recording_id, include_deleted=True)
            if existing is None:  # pragma: no cover
                raise
            return existing, False

    existing = await get_by_recording_id(db, recording_id, include_deleted=True)
    if existing is not None:
        return existing, False
    created = await create_transcript(
        db,
        recording_id=recording_id,
        status=status,
        commit=commit,
    )
    return created, True
