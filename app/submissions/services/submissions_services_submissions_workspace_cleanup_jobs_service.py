"""Application module for submissions services submissions workspace cleanup jobs service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Job
from app.shared.jobs.repositories import repository as jobs_repo

WORKSPACE_CLEANUP_JOB_TYPE = "workspace_cleanup"
WORKSPACE_CLEANUP_MAX_ATTEMPTS = 8


def workspace_cleanup_idempotency_key(company_id: int, *, run_key: str) -> str:
    """Execute workspace cleanup idempotency key."""
    normalized_run_key = run_key.strip()
    if not normalized_run_key:
        raise ValueError("run_key is required")
    return f"workspace_cleanup:{company_id}:{normalized_run_key}"


def build_workspace_cleanup_payload(
    *,
    company_id: int,
    run_key: str,
) -> dict[str, Any]:
    """Build workspace cleanup payload."""
    return {
        "companyId": company_id,
        "runKey": run_key,
    }


async def enqueue_workspace_cleanup_job(
    db: AsyncSession,
    *,
    company_id: int,
    run_key: str | None = None,
    commit: bool = False,
) -> Job:
    """Enqueue workspace cleanup job."""
    resolved_run_key = run_key or datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    payload = build_workspace_cleanup_payload(
        company_id=company_id,
        run_key=resolved_run_key,
    )
    return await jobs_repo.create_or_get_idempotent(
        db,
        job_type=WORKSPACE_CLEANUP_JOB_TYPE,
        idempotency_key=workspace_cleanup_idempotency_key(
            company_id,
            run_key=resolved_run_key,
        ),
        payload_json=payload,
        company_id=company_id,
        max_attempts=WORKSPACE_CLEANUP_MAX_ATTEMPTS,
        correlation_id=f"workspace_cleanup:{company_id}",
        commit=commit,
    )


__all__ = [
    "WORKSPACE_CLEANUP_JOB_TYPE",
    "WORKSPACE_CLEANUP_MAX_ATTEMPTS",
    "build_workspace_cleanup_payload",
    "enqueue_workspace_cleanup_job",
    "workspace_cleanup_idempotency_key",
]
