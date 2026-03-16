from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.transcripts.models import Transcript

_UNSET = object()


async def get_by_recording_id(
    db: AsyncSession,
    recording_id: int,
    *,
    include_deleted: bool = False,
) -> Transcript | None:
    stmt = select(Transcript).where(Transcript.recording_id == recording_id)
    if not include_deleted:
        stmt = stmt.where(Transcript.deleted_at.is_(None))
    return (await db.execute(stmt)).scalar_one_or_none()


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
    existing = await get_by_recording_id(
        db,
        recording_id,
        include_deleted=True,
    )
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


async def hard_delete_by_recording_id(
    db: AsyncSession,
    recording_id: int,
    *,
    commit: bool = True,
) -> int:
    result = await db.execute(
        delete(Transcript).where(Transcript.recording_id == recording_id)
    )
    deleted_count = int(result.rowcount or 0)
    if commit:
        await db.commit()
    return deleted_count


__all__ = [
    "create_transcript",
    "hard_delete_by_recording_id",
    "get_by_recording_id",
    "get_or_create_transcript",
    "mark_deleted",
    "update_transcript",
    "update_status",
]
