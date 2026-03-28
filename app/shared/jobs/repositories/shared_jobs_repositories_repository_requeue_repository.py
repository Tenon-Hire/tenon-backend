"""Application module for jobs repositories repository requeue repository workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    Job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    load_idempotent_job,
    validate_payload_size,
)


async def requeue_nonterminal_idempotent_job(
    db: AsyncSession,
    *,
    company_id: int,
    job_type: str,
    idempotency_key: str,
    next_run_at: datetime,
    now: datetime,
    payload_json: dict[str, Any] | None = None,
    commit: bool = True,
) -> Job | None:
    """Requeue nonterminal idempotent job."""
    normalized_type = job_type.strip()
    normalized_key = idempotency_key.strip()
    if not normalized_type:
        raise ValueError("job_type is required")
    if not normalized_key:
        raise ValueError("idempotency_key is required")
    if payload_json is not None:
        validate_payload_size(payload_json)
    updates: dict[str, object] = {
        "status": JOB_STATUS_QUEUED,
        "next_run_at": next_run_at,
        "last_error": None,
        "locked_at": None,
        "locked_by": None,
        "updated_at": now,
    }
    if payload_json is not None:
        updates["payload_json"] = payload_json
    result = await db.execute(
        update(Job)
        .where(
            Job.company_id == company_id,
            Job.job_type == normalized_type,
            Job.idempotency_key == normalized_key,
            Job.status.in_((JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)),
        )
        .values(**updates)
    )
    if result.rowcount == 0:
        return None
    if commit:
        await db.commit()
    else:
        await db.flush()
    return await load_idempotent_job(
        db,
        company_id=company_id,
        job_type=normalized_type,
        idempotency_key=normalized_key,
    )
