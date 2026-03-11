from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
    RECORDING_ASSET_STATUS_UPLOADED,
    RecordingAsset,
)

DOWNLOADABLE_RECORDING_STATUSES = {
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
}


async def create_recording_asset(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    storage_key: str,
    content_type: str,
    bytes_count: int,
    status: str,
    created_at: datetime | None = None,
    commit: bool = True,
) -> RecordingAsset:
    recording = RecordingAsset(
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        storage_key=storage_key,
        content_type=content_type,
        bytes=bytes_count,
        status=status,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(recording)
    if commit:
        await db.commit()
        await db.refresh(recording)
    else:
        await db.flush()
    return recording


async def get_by_id(db: AsyncSession, recording_id: int) -> RecordingAsset | None:
    stmt = select(RecordingAsset).where(RecordingAsset.id == recording_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_id_for_update(
    db: AsyncSession, recording_id: int
) -> RecordingAsset | None:
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


async def update_status(
    db: AsyncSession,
    *,
    recording: RecordingAsset,
    status: str,
    commit: bool = True,
) -> RecordingAsset:
    if recording.status != status:
        recording.status = status
    if commit:
        await db.commit()
        await db.refresh(recording)
    else:
        await db.flush()
    return recording


def is_downloadable(recording: RecordingAsset | None) -> bool:
    if recording is None:
        return False
    return recording.status in DOWNLOADABLE_RECORDING_STATUSES


__all__ = [
    "DOWNLOADABLE_RECORDING_STATUSES",
    "create_recording_asset",
    "get_by_id",
    "get_by_id_for_update",
    "get_latest_for_task_session",
    "is_downloadable",
    "update_status",
]
