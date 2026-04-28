"""Application module for media repositories recordings media recordings queries repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_KIND_RECORDING,
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_READY,
    RECORDING_ASSET_STATUS_UPLOADED,
    RecordingAsset,
)
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_predicates_repository import (
    DOWNLOADABLE_RECORDING_STATUSES,
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
    asset_kind: str | None = None,
) -> RecordingAsset | None:
    """Return latest for task session."""
    stmt = select(RecordingAsset).where(
        RecordingAsset.candidate_session_id == candidate_session_id,
        RecordingAsset.task_id == task_id,
    )
    if asset_kind is not None:
        stmt = stmt.where(RecordingAsset.asset_kind == asset_kind)
    stmt = stmt.order_by(
        RecordingAsset.created_at.desc(), RecordingAsset.id.desc()
    ).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_playback_safe_for_task_session(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
) -> RecordingAsset | None:
    """Return the latest recording that is safe to surface for playback."""
    stmt = (
        select(RecordingAsset)
        .where(
            RecordingAsset.candidate_session_id == candidate_session_id,
            RecordingAsset.task_id == task_id,
            RecordingAsset.asset_kind == RECORDING_ASSET_KIND_RECORDING,
            RecordingAsset.status.in_(DOWNLOADABLE_RECORDING_STATUSES),
            RecordingAsset.deleted_at.is_(None),
            RecordingAsset.purged_at.is_(None),
        )
        .order_by(RecordingAsset.created_at.desc(), RecordingAsset.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_for_task_session(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    asset_kind: str | None = None,
) -> list[RecordingAsset]:
    """Return all assets for a task session."""
    stmt = select(RecordingAsset).where(
        RecordingAsset.candidate_session_id == candidate_session_id,
        RecordingAsset.task_id == task_id,
    )
    if asset_kind is not None:
        stmt = stmt.where(RecordingAsset.asset_kind == asset_kind)
    stmt = stmt.order_by(RecordingAsset.created_at.asc(), RecordingAsset.id.asc())
    return list((await db.execute(stmt)).scalars().all())


async def get_expired_for_retention(
    db: AsyncSession,
    *,
    retention_days: int,
    now: datetime | None = None,
    limit: int = 200,
) -> list[RecordingAsset]:
    """Return expired for retention."""
    resolved_now = now or datetime.now(UTC)
    cutoff = resolved_now - timedelta(days=max(1, int(retention_days)))
    stmt = (
        select(RecordingAsset)
        .where(
            RecordingAsset.purged_at.is_(None),
            RecordingAsset.status.in_(
                (
                    RECORDING_ASSET_STATUS_UPLOADED,
                    RECORDING_ASSET_STATUS_READY,
                    RECORDING_ASSET_STATUS_FAILED,
                    RECORDING_ASSET_STATUS_DELETED,
                )
            ),
            (
                (RecordingAsset.retention_expires_at.is_not(None))
                & (RecordingAsset.retention_expires_at <= resolved_now)
            )
            | (
                (RecordingAsset.retention_expires_at.is_(None))
                & (RecordingAsset.created_at <= cutoff)
            ),
        )
        .order_by(RecordingAsset.created_at.asc(), RecordingAsset.id.asc())
        .limit(max(1, int(limit)))
    )
    return (await db.execute(stmt)).scalars().all()


async def list_for_candidate_session(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    include_purged: bool = False,
    limit: int = 500,
) -> list[RecordingAsset]:
    """Return media assets scoped to a Candidate session."""
    stmt = select(RecordingAsset).where(
        RecordingAsset.candidate_session_id == candidate_session_id
    )
    if not include_purged:
        stmt = stmt.where(RecordingAsset.purged_at.is_(None))
    stmt = stmt.order_by(
        RecordingAsset.created_at.asc(), RecordingAsset.id.asc()
    ).limit(max(1, int(limit)))
    return (await db.execute(stmt)).scalars().all()
