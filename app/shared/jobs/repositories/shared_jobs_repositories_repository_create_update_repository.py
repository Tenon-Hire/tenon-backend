"""Application module for jobs repositories repository create update repository workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import Job
from app.shared.jobs.repositories.shared_jobs_repositories_repository_create_get_repository import (
    create_or_get_idempotent,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    apply_idempotent_job_updates,
    is_mutable_idempotent_job,
    load_idempotent_job,
    normalize_idempotent_create_inputs,
    validate_payload_size,
)


async def create_or_update_idempotent(
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
    """Create or update idempotent."""
    normalized_type, normalized_key = normalize_idempotent_create_inputs(
        job_type=job_type, idempotency_key=idempotency_key, max_attempts=max_attempts
    )
    validate_payload_size(payload_json)
    existing = await load_idempotent_job(
        db,
        company_id=company_id,
        job_type=normalized_type,
        idempotency_key=normalized_key,
    )
    if existing is not None:
        await _update_existing_if_mutable(
            db,
            job=existing,
            payload_json=payload_json,
            candidate_session_id=candidate_session_id,
            max_attempts=max_attempts,
            correlation_id=correlation_id,
            next_run_at=next_run_at,
            commit=commit,
        )
        return existing
    job = await create_or_get_idempotent(
        db,
        job_type=normalized_type,
        idempotency_key=normalized_key,
        payload_json=payload_json,
        company_id=company_id,
        candidate_session_id=candidate_session_id,
        max_attempts=max_attempts,
        correlation_id=correlation_id,
        next_run_at=next_run_at,
        commit=commit,
    )
    await _update_existing_if_mutable(
        db,
        job=job,
        payload_json=payload_json,
        candidate_session_id=candidate_session_id,
        max_attempts=max_attempts,
        correlation_id=correlation_id,
        next_run_at=next_run_at,
        commit=commit,
    )
    return job


async def _update_existing_if_mutable(
    db: AsyncSession,
    *,
    job: Job,
    payload_json: dict[str, Any],
    candidate_session_id: int | None,
    max_attempts: int,
    correlation_id: str | None,
    next_run_at: datetime | None,
    commit: bool,
) -> None:
    if not is_mutable_idempotent_job(job):
        return
    apply_idempotent_job_updates(
        job,
        payload_json=payload_json,
        candidate_session_id=candidate_session_id,
        max_attempts=max_attempts,
        correlation_id=correlation_id,
        next_run_at=next_run_at,
    )
    if commit:
        await db.commit()
        await db.refresh(job)
    else:
        await db.flush()
