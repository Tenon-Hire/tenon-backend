"""Application module for Talent Partners services Talent Partners admin ops job helpers service workflows."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.database.shared_database_models_model import Job
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_RUNNING,
)
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_audit_service import (
    normalize_datetime,
)


async def load_job_for_update(db: AsyncSession, job_id: str) -> Job:
    """Load job for update."""
    job = (
        await db.execute(select(Job).where(Job.id == job_id).with_for_update())
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


def job_stale_seconds() -> int:
    """Execute job stale seconds."""
    configured = int(settings.DEMO_ADMIN_JOB_STALE_SECONDS or 0)
    return configured if configured > 0 else 900


def is_stale_running_job(job: Job, *, now: datetime) -> bool:
    """Return whether stale running job."""
    if job.status != JOB_STATUS_RUNNING:
        return False
    locked_at = normalize_datetime(job.locked_at)
    if locked_at is None:
        return True
    stale_before = now - timedelta(seconds=job_stale_seconds())
    return locked_at <= stale_before


__all__ = ["is_stale_running_job", "job_stale_seconds", "load_job_for_update"]
