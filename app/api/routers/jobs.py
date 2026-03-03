from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.principal import Principal, get_principal
from app.core.db import get_session
from app.core.errors import ApiError
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import JOB_STATUS_QUEUED, JOB_STATUS_RUNNING
from app.schemas.jobs import JobStatusResponse

router = APIRouter(prefix="/jobs")

ACTIVE_POLL_AFTER_MS = 1500
TERMINAL_POLL_AFTER_MS = 0


def _poll_after_ms_for_status(status_value: str) -> int:
    if status_value in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        return ACTIVE_POLL_AFTER_MS
    return TERMINAL_POLL_AFTER_MS


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
    return JobStatusResponse(
        jobId=job.id,
        jobType=job.job_type,
        status=job.status,
        attempt=job.attempt,
        maxAttempts=job.max_attempts,
        pollAfterMs=_poll_after_ms_for_status(job.status),
        result=result,
        error=job.last_error,
    )
