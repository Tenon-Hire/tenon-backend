"""Application module for jobs repositories repository create get repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    Job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    load_idempotent_job,
    normalize_idempotent_create_inputs,
    validate_payload_size,
)


async def create_or_get_idempotent(
    db: AsyncSession,
    *,
    job_type: str,
    idempotency_key: str,
    payload_json: dict[str, Any],
    company_id: int,
    candidate_session_id: int | None = None,
    max_attempts: int = 5,
    correlation_id: str | None = None,
    next_run_at: datetime | None = None,
    commit: bool = True,
) -> Job:
    """Create or get idempotent."""
    normalized_type, normalized_key = normalize_idempotent_create_inputs(
        job_type=job_type, idempotency_key=idempotency_key, max_attempts=max_attempts
    )
    validate_payload_size(payload_json)
    job = Job(
        job_type=normalized_type,
        status=JOB_STATUS_QUEUED,
        attempt=0,
        max_attempts=max_attempts,
        idempotency_key=normalized_key,
        payload_json=payload_json,
        result_json=None,
        last_error=None,
        next_run_at=next_run_at or datetime.now(UTC),
        locked_at=None,
        locked_by=None,
        correlation_id=correlation_id,
        company_id=company_id,
        candidate_session_id=candidate_session_id,
    )
    if not commit:
        return await _insert_nested_or_get_existing(
            db,
            job=job,
            company_id=company_id,
            job_type=normalized_type,
            idempotency_key=normalized_key,
        )
    return await _insert_commit_or_get_existing(
        db,
        job=job,
        company_id=company_id,
        job_type=normalized_type,
        idempotency_key=normalized_key,
    )


async def _insert_nested_or_get_existing(
    db: AsyncSession, *, job: Job, company_id: int, job_type: str, idempotency_key: str
) -> Job:
    try:
        async with db.begin_nested():
            db.add(job)
            await db.flush()
    except IntegrityError:
        existing = await load_idempotent_job(
            db,
            company_id=company_id,
            job_type=job_type,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise
        return existing
    return job


async def _insert_commit_or_get_existing(
    db: AsyncSession, *, job: Job, company_id: int, job_type: str, idempotency_key: str
) -> Job:
    existing = await load_idempotent_job(
        db, company_id=company_id, job_type=job_type, idempotency_key=idempotency_key
    )
    if existing is not None:
        return existing
    db.add(job)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await load_idempotent_job(
            db,
            company_id=company_id,
            job_type=job_type,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise
        return existing
    await db.refresh(job)
    return job
