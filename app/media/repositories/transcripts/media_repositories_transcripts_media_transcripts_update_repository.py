"""Application module for media repositories transcripts media transcripts update repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    Transcript,
)

_UNSET = object()


async def update_status(
    db: AsyncSession,
    *,
    transcript: Transcript,
    status: str,
    commit: bool = True,
) -> Transcript:
    """Update status."""
    if transcript.status != status:
        transcript.status = status
    if commit:
        await db.commit()
        await db.refresh(transcript)
    else:
        await db.flush()
    return transcript


async def update_transcript(
    db: AsyncSession,
    *,
    transcript: Transcript,
    status: str | object = _UNSET,
    text: str | None | object = _UNSET,
    segments_json: list[dict[str, Any]] | None | object = _UNSET,
    model_name: str | None | object = _UNSET,
    last_error: str | None | object = _UNSET,
    commit: bool = True,
) -> Transcript:
    """Update transcript."""
    if status is not _UNSET:
        transcript.status = status
    if text is not _UNSET:
        transcript.text = text
    if segments_json is not _UNSET:
        transcript.segments_json = segments_json
    if model_name is not _UNSET:
        transcript.model_name = model_name
    if last_error is not _UNSET:
        transcript.last_error = last_error
    if commit:
        await db.commit()
        await db.refresh(transcript)
    else:
        await db.flush()
    return transcript


async def mark_deleted(
    db: AsyncSession,
    *,
    transcript: Transcript,
    now: datetime | None = None,
    commit: bool = True,
) -> Transcript:
    """Mark deleted."""
    if transcript.deleted_at is None:
        transcript.deleted_at = now or datetime.now(UTC)
    transcript.text = None
    transcript.segments_json = None
    if commit:
        await db.commit()
        await db.refresh(transcript)
    else:
        await db.flush()
    return transcript
