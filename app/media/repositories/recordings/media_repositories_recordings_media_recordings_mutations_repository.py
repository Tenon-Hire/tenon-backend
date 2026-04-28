"""Application module for media repositories recordings media recordings mutations repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_KIND_RECORDING,
    RECORDING_ASSET_PURGE_STATUS_PURGED,
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_PURGED,
    RecordingAsset,
)


async def create_recording_asset(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    storage_key: str,
    content_type: str,
    bytes_count: int,
    asset_kind: str = RECORDING_ASSET_KIND_RECORDING,
    status: str,
    duration_seconds: int | None = None,
    consent_version: str | None = None,
    consent_timestamp: datetime | None = None,
    ai_notice_version: str | None = None,
    retention_expires_at: datetime | None = None,
    created_at: datetime | None = None,
    commit: bool = True,
) -> RecordingAsset:
    """Create recording asset."""
    recording = RecordingAsset(
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        storage_key=storage_key,
        content_type=content_type,
        bytes=bytes_count,
        asset_kind=asset_kind,
        duration_seconds=duration_seconds,
        status=status,
        consent_version=consent_version,
        consent_timestamp=consent_timestamp,
        ai_notice_version=ai_notice_version,
        retention_expires_at=retention_expires_at,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(recording)
    if commit:
        await db.commit()
        await db.refresh(recording)
    else:
        await db.flush()
    return recording


async def update_status(
    db: AsyncSession,
    *,
    recording: RecordingAsset,
    status: str,
    commit: bool = True,
) -> RecordingAsset:
    """Update status."""
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
    """Mark deleted."""
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
    purge_reason: str,
    now: datetime | None = None,
    commit: bool = True,
) -> RecordingAsset:
    """Mark purged."""
    resolved_now = now or datetime.now(UTC)
    if recording.deleted_at is None:
        recording.deleted_at = resolved_now
    if recording.purged_at is None:
        recording.purged_at = resolved_now
    recording.status = RECORDING_ASSET_STATUS_PURGED
    recording.purge_reason = purge_reason
    recording.purge_status = RECORDING_ASSET_PURGE_STATUS_PURGED
    if commit:
        await db.commit()
        await db.refresh(recording)
    else:
        await db.flush()
    return recording
