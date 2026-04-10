"""Application module for evaluations services evaluations winoe report api helpers service workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_FAILED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)
from app.shared.database.shared_database_models_model import Job
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)


async def has_active_evaluation_job(
    db,
    *,
    candidate_session_id: int,
    job_type: str,
) -> bool:
    """Execute has active evaluation job."""
    stmt = (
        select(Job.id)
        .where(
            Job.candidate_session_id == candidate_session_id,
            Job.job_type == job_type,
            Job.status.in_((JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


def build_latest_run_status(latest_run: Any) -> dict[str, Any]:
    """Build latest run status."""
    if latest_run.status in {
        EVALUATION_RUN_STATUS_PENDING,
        EVALUATION_RUN_STATUS_RUNNING,
    }:
        return {"status": "running"}
    if latest_run.status == EVALUATION_RUN_STATUS_FAILED:
        return {
            "status": "failed",
            "errorCode": latest_run.error_code or "evaluation_failed",
        }
    return {"status": "not_started"}
