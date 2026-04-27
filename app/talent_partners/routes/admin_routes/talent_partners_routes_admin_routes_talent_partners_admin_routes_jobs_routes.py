"""Operator job controls."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_session
from app.shared.http.dependencies.shared_http_dependencies_admin_operator_utils import (
    DemoAdminActor,
    require_operator_admin,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
)
from app.shared.jobs.shared_jobs_dead_letter_retry_service import retry_dead_letter_job
from app.shared.jobs.shared_jobs_failure_summaries_service import (
    FailedJobsListResponse,
    SafeFailedJobSummary,
    list_failed_jobs,
    safe_failed_job_summary,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_audit_service import (
    insert_audit,
    log_admin_action,
)

router = APIRouter()

JOB_RETRY_ACTION = "job_retry"


@router.get(
    "/jobs/failed",
    response_model=FailedJobsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Failed Jobs",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required."},
    },
)
async def list_failed_operator_jobs(
    db: Annotated[AsyncSession, Depends(get_session)],
    _actor: Annotated[DemoAdminActor, Depends(require_operator_admin)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FailedJobsListResponse:
    """List dead-letter durable jobs with safe metadata."""
    return await list_failed_jobs(db, limit=limit, offset=offset)


@router.post(
    "/jobs/{job_id}/retry",
    response_model=SafeFailedJobSummary,
    status_code=status.HTTP_200_OK,
    summary="Retry Failed Job",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Job not found."},
        status.HTTP_409_CONFLICT: {"description": "Job is not retryable."},
    },
)
async def retry_operator_job(
    job_id: Annotated[str, Path(..., min_length=1, max_length=64)],
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_operator_admin)],
) -> SafeFailedJobSummary:
    """Retry one dead-letter durable job."""
    job = await jobs_repo.get_by_id(db, job_id)
    if job is None:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
            error_code="JOB_NOT_FOUND",
            retryable=False,
        )
    if job.status != JOB_STATUS_DEAD_LETTER:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is not in a retryable failed state.",
            error_code="JOB_NOT_RETRYABLE",
            retryable=False,
            details={"jobId": job_id, "status": job.status},
        )

    updated_job = await retry_dead_letter_job(
        db,
        job_id=job_id,
        now=datetime.now(UTC),
        commit=False,
    )
    if updated_job is None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is not in a retryable failed state.",
            error_code="JOB_NOT_RETRYABLE",
            retryable=False,
            details={"jobId": job_id},
        )
    audit_id = await insert_audit(
        db,
        actor=actor,
        action=JOB_RETRY_ACTION,
        target_type="job",
        target_id=job_id,
        payload={
            "previousStatus": JOB_STATUS_DEAD_LETTER,
            "newStatus": updated_job.status,
        },
    )
    await db.commit()
    log_admin_action(
        audit_id=audit_id,
        action=JOB_RETRY_ACTION,
        target_type="job",
        target_id=job_id,
        actor_id=actor.actor_id,
    )
    await db.refresh(updated_job)
    return safe_failed_job_summary(updated_job)


__all__ = [
    "JOB_RETRY_ACTION",
    "list_failed_operator_jobs",
    "retry_operator_job",
    "router",
]
