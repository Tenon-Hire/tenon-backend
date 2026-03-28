"""Application module for jobs worker runtime state writes service workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.jobs.repositories import repository as jobs_repo


async def mark_dead_letter(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    job_id: str,
    error_str: str,
    claim_time: datetime,
) -> None:
    """Mark dead letter."""
    async with session_maker() as db:
        await jobs_repo.mark_dead_letter(
            db, job_id=job_id, error_str=error_str, now=claim_time
        )


async def mark_failed_and_reschedule(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    job_id: str,
    error_str: str,
    next_run_at: datetime,
    claim_time: datetime,
) -> None:
    """Mark failed and reschedule."""
    async with session_maker() as db:
        await jobs_repo.mark_failed_and_reschedule(
            db,
            job_id=job_id,
            error_str=error_str,
            next_run_at=next_run_at,
            now=claim_time,
        )


async def get_job_by_id(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    job_id: str,
) -> Any:
    """Return job by id."""
    async with session_maker() as db:
        return await jobs_repo.get_by_id(db, job_id)


async def mark_succeeded(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    job_id: str,
    result: dict[str, Any] | None,
    claim_time: datetime,
) -> None:
    """Mark succeeded."""
    async with session_maker() as db:
        await jobs_repo.mark_succeeded(
            db, job_id=job_id, result_json=result, now=claim_time
        )


__all__ = [
    "get_job_by_id",
    "mark_dead_letter",
    "mark_failed_and_reschedule",
    "mark_succeeded",
]
