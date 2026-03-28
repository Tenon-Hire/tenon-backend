"""Application module for http routes jobs routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.principal import Principal, get_principal
from app.shared.database import get_session
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
)
from app.shared.jobs.schemas.shared_jobs_schemas_jobs_schema import JobStatusResponse
from app.shared.utils.shared_utils_errors_utils import ApiError

router = APIRouter(prefix="/jobs")

ACTIVE_POLL_AFTER_MS = 1500
TERMINAL_POLL_AFTER_MS = 0


def _poll_after_ms_for_status(status_value: str) -> int:
    if status_value in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        return ACTIVE_POLL_AFTER_MS
    return TERMINAL_POLL_AFTER_MS


def _public_job_status(internal_status: str) -> str:
    # Durable job rows persist terminal states as succeeded/dead_letter. The
    # public polling contract (including scenario_generation jobs) uses
    # completed/failed so clients never depend on storage-level labels.
    if internal_status == JOB_STATUS_SUCCEEDED:
        return "completed"
    if internal_status == JOB_STATUS_DEAD_LETTER:
        return "failed"
    return internal_status


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_job_status(
    job_id: Annotated[str, Path(..., min_length=1, max_length=64)],
    db: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_principal)],
) -> JobStatusResponse:
    """Return a single durable job status if visible to the authenticated principal."""
    job = await jobs_repo.get_by_id_for_principal(db, job_id, principal)
    if job is None:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
            error_code="JOB_NOT_FOUND",
            retryable=False,
        )

    result: dict[str, Any] | None = (
        job.result_json if isinstance(job.result_json, dict) else None
    )
    public_status = _public_job_status(job.status)
    return JobStatusResponse(
        jobId=job.id,
        jobType=job.job_type,
        status=public_status,
        attempt=job.attempt,
        maxAttempts=job.max_attempts,
        pollAfterMs=_poll_after_ms_for_status(job.status),
        result=result,
        error=job.last_error,
    )
