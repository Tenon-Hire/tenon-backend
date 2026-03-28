"""Application module for media repositories recordings media recordings queries repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RecordingAsset,
)


async def get_by_id(db: AsyncSession, recording_id: int) -> RecordingAsset | None:
    """Return by id."""
    stmt = select(RecordingAsset).where(RecordingAsset.id == recording_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_id_for_update(
    db: AsyncSession, recording_id: int
) -> RecordingAsset | None:
    """Return by id for update."""
    stmt = (
        select(RecordingAsset)
        .where(RecordingAsset.id == recording_id)
        .with_for_update()
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_for_task_session(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
) -> RecordingAsset | None:
    """Return latest for task session."""
    stmt = (
        select(RecordingAsset)
        .where(
            RecordingAsset.candidate_session_id == candidate_session_id,
            RecordingAsset.task_id == task_id,
        )
        .order_by(RecordingAsset.created_at.desc(), RecordingAsset.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_expired_for_retention(
    db: AsyncSession,
    *,
    retention_days: int,
    now: datetime | None = None,
    limit: int = 200,
) -> list[RecordingAsset]:
    """Return expired for retention."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=max(1, int(retention_days)))
    stmt = (
        select(RecordingAsset)
        .where(RecordingAsset.created_at <= cutoff, RecordingAsset.purged_at.is_(None))
        .order_by(RecordingAsset.created_at.asc(), RecordingAsset.id.asc())
        .limit(max(1, int(limit)))
    )
    return (await db.execute(stmt)).scalars().all()
