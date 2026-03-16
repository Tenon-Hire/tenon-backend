from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_PURGED,
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
    consent_version: str | None = None,
    consent_timestamp: datetime | None = None,
    ai_notice_version: str | None = None,
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
        consent_version=consent_version,
        consent_timestamp=consent_timestamp,
        ai_notice_version=ai_notice_version,
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


async def mark_deleted(
    db: AsyncSession,
    *,
    recording: RecordingAsset,
    now: datetime | None = None,
    commit: bool = True,
) -> RecordingAsset:
    resolved_now = now or datetime.now(UTC)
    if recording.deleted_at is None:
        recording.deleted_at = resolved_now
    if recording.status != RECORDING_ASSET_STATUS_PURGED:
        recording.status = RECORDING_ASSET_STATUS_DELETED
    if commit:
        await db.commit()
        await db.refresh(recording)
    else:
        await db.flush()
    return recording


async def mark_purged(
    db: AsyncSession,
    *,
    recording: RecordingAsset,
    now: datetime | None = None,
    commit: bool = True,
) -> RecordingAsset:
    resolved_now = now or datetime.now(UTC)
    if recording.deleted_at is None:
        recording.deleted_at = resolved_now
    if recording.purged_at is None:
        recording.purged_at = resolved_now
    recording.status = RECORDING_ASSET_STATUS_PURGED
    if commit:
        await db.commit()
        await db.refresh(recording)
    else:
        await db.flush()
    return recording


async def get_expired_for_retention(
    db: AsyncSession,
    *,
    retention_days: int,
    now: datetime | None = None,
    limit: int = 200,
) -> list[RecordingAsset]:
    retention_window_days = max(1, int(retention_days))
    # Retention is intentionally anchored to object creation time so media has a
    # deterministic maximum lifetime regardless of later state transitions.
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_window_days)
    fetch_limit = max(1, int(limit))
    stmt = (
        select(RecordingAsset)
        .where(
            RecordingAsset.created_at <= cutoff,
            RecordingAsset.purged_at.is_(None),
        )
        .order_by(RecordingAsset.created_at.asc(), RecordingAsset.id.asc())
        .limit(fetch_limit)
    )
    return (await db.execute(stmt)).scalars().all()


def is_deleted_or_purged(recording: RecordingAsset | None) -> bool:
    if recording is None:
        return False
    deleted_at = getattr(recording, "deleted_at", None)
    purged_at = getattr(recording, "purged_at", None)
    status = getattr(recording, "status", None)
    if deleted_at is not None or purged_at is not None:
        return True
    return status in {
        RECORDING_ASSET_STATUS_DELETED,
        RECORDING_ASSET_STATUS_PURGED,
    }


def is_downloadable(recording: RecordingAsset | None) -> bool:
    if recording is None:
        return False
    if is_deleted_or_purged(recording):
        return False
    return recording.status in DOWNLOADABLE_RECORDING_STATUSES


__all__ = [
    "DOWNLOADABLE_RECORDING_STATUSES",
    "create_recording_asset",
    "get_expired_for_retention",
    "get_by_id",
    "get_by_id_for_update",
    "get_latest_for_task_session",
    "is_deleted_or_purged",
    "is_downloadable",
    "mark_deleted",
    "mark_purged",
    "update_status",
]
