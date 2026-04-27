"""Application module for dead-letter job retry service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.database import async_session_maker
from app.shared.jobs.repositories import repository as jobs_repo


async def retry_dead_letter_jobs(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    job_ids: list[str] | None = None,
    now: datetime | None = None,
) -> int:
    """Retry dead-letter jobs."""
    resolved_now = now or datetime.now(UTC)
    async with session_maker() as db:
        return await jobs_repo.requeue_dead_letter_jobs(
            db,
            now=resolved_now,
            job_ids=job_ids,
        )


async def retry_dead_letter_job(
    db: AsyncSession,
    *,
    job_id: str,
    now: datetime | None = None,
    commit: bool = True,
):
    """Retry one dead-letter job using the same state transition as the CLI."""
    resolved_now = now or datetime.now(UTC)
    return await jobs_repo.requeue_dead_letter_job(
        db,
        job_id=job_id,
        now=resolved_now,
        commit=commit,
    )


__all__ = ["retry_dead_letter_job", "retry_dead_letter_jobs"]
