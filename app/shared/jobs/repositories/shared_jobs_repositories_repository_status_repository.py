"""Application module for jobs repositories repository status repository workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
    Job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    sanitize_error,
)


async def mark_succeeded(
    db: AsyncSession, *, job_id: str, result_json: dict[str, Any] | None, now
) -> None:
    """Mark succeeded."""
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JOB_STATUS_SUCCEEDED,
            result_json=result_json,
            last_error=None,
            next_run_at=None,
            locked_at=None,
            locked_by=None,
            updated_at=now,
        )
    )
    await db.commit()


async def mark_failed_and_reschedule(
    db: AsyncSession, *, job_id: str, error_str: str, next_run_at, now
) -> None:
    """Mark failed and reschedule."""
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JOB_STATUS_QUEUED,
            last_error=sanitize_error(error_str),
            next_run_at=next_run_at,
            locked_at=None,
            locked_by=None,
            updated_at=now,
        )
    )
    await db.commit()


async def mark_dead_letter(
    db: AsyncSession, *, job_id: str, error_str: str, now
) -> None:
    """Mark dead letter."""
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JOB_STATUS_DEAD_LETTER,
            last_error=sanitize_error(error_str),
            next_run_at=None,
            locked_at=None,
            locked_by=None,
            updated_at=now,
        )
    )
    await db.commit()
