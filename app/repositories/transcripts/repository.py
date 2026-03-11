from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.transcripts.models import Transcript


async def get_by_recording_id(db: AsyncSession, recording_id: int) -> Transcript | None:
    stmt = select(Transcript).where(Transcript.recording_id == recording_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_transcript(
    db: AsyncSession,
    *,
    recording_id: int,
    status: str,
    text: str | None = None,
    segments_json: list[dict[str, Any]] | None = None,
    model_name: str | None = None,
    created_at: datetime | None = None,
    commit: bool = True,
) -> Transcript:
    transcript = Transcript(
        recording_id=recording_id,
        status=status,
        text=text,
        segments_json=segments_json,
        model_name=model_name,
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
    existing = await get_by_recording_id(db, recording_id)
    if existing is not None:
        return existing, False
    created = await create_transcript(
        db,
        recording_id=recording_id,
        status=status,
        commit=commit,
    )
    return created, True


async def update_status(
    db: AsyncSession,
    *,
    transcript: Transcript,
    status: str,
    commit: bool = True,
) -> Transcript:
    if transcript.status != status:
        transcript.status = status
    if commit:
        await db.commit()
        await db.refresh(transcript)
    else:
        await db.flush()
    return transcript


__all__ = [
    "create_transcript",
    "get_by_recording_id",
    "get_or_create_transcript",
    "update_status",
]
