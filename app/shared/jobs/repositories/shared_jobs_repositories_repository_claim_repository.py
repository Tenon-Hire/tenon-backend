"""Application module for jobs repositories repository claim repository workflows."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    Job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_lookup_repository import (
    get_by_id,
)


def runnable_filter(now, *, stale_before):
    """Execute runnable filter."""
    return or_(
        and_(
            Job.status == JOB_STATUS_QUEUED,
            or_(Job.next_run_at.is_(None), Job.next_run_at <= now),
        ),
        and_(
            Job.status == JOB_STATUS_RUNNING,
            or_(Job.locked_at.is_(None), Job.locked_at <= stale_before),
        ),
    )


async def claim_next_runnable(
    db: AsyncSession,
    *,
    worker_id: str,
    now,
    lease_seconds: int,
) -> Job | None:
    """Claim next runnable."""
    stale_before = now - timedelta(seconds=lease_seconds)
    order = (func.coalesce(Job.next_run_at, Job.created_at).asc(), Job.created_at.asc())
    for _ in range(8):
        candidate_row = (
            await db.execute(
                select(Job.id, Job.attempt)
                .where(runnable_filter(now, stale_before=stale_before))
                .order_by(*order)
                .limit(1)
            )
        ).first()
        if candidate_row is None:
            return None
        current_attempt = int(candidate_row.attempt)
        claimed = await db.execute(
            update(Job)
            .where(
                Job.id == candidate_row.id,
                Job.attempt == current_attempt,
                runnable_filter(now, stale_before=stale_before),
            )
            .values(
                status=JOB_STATUS_RUNNING,
                attempt=current_attempt + 1,
                locked_at=now,
                locked_by=worker_id,
                updated_at=now,
            )
        )
        if claimed.rowcount == 1:
            await db.commit()
            return await get_by_id(db, candidate_row.id)
        await db.rollback()
    return None
