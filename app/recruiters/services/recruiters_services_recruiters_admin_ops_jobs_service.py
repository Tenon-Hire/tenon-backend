"""Application module for recruiters services recruiters admin ops jobs service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.recruiters.services.recruiters_services_recruiters_admin_ops_audit_service import (
    insert_audit,
    log_admin_action,
    normalize_datetime,
    sanitized_reason,
    unsafe_operation,
)
from app.recruiters.services.recruiters_services_recruiters_admin_ops_job_helpers_service import (
    is_stale_running_job,
    job_stale_seconds,
    load_job_for_update,
)
from app.recruiters.services.recruiters_services_recruiters_admin_ops_types_service import (
    JOB_REQUEUE_ACTION,
    JobRequeueResult,
)
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    DemoAdminActor,
)
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
)


async def requeue_job(
    db: AsyncSession,
    *,
    actor: DemoAdminActor,
    job_id: str,
    reason: str,
    force: bool,
    now: datetime | None = None,
) -> JobRequeueResult:
    """Requeue job."""
    resolved_now = normalize_datetime(now) or datetime.now(UTC)
    job = await load_job_for_update(db, job_id)
    previous_status = job.status
    stale_running = is_stale_running_job(job, now=resolved_now)
    no_op = job.status == JOB_STATUS_QUEUED
    if not no_op:
        if force and job.status not in {
            JOB_STATUS_RUNNING,
            JOB_STATUS_DEAD_LETTER,
            JOB_STATUS_SUCCEEDED,
        }:
            unsafe_operation(
                "Job cannot be force requeued from its current status.",
                details={"jobId": job_id, "status": job.status},
            )
        if not force and job.status != JOB_STATUS_DEAD_LETTER and not stale_running:
            unsafe_operation(
                "Job cannot be requeued without force from its current status.",
                details={
                    "jobId": job_id,
                    "status": job.status,
                    "staleRunningThresholdSeconds": job_stale_seconds(),
                },
            )
        job.status = JOB_STATUS_QUEUED
        job.next_run_at = resolved_now
        job.locked_at = None
        job.locked_by = None
        job.last_error = None
        job.result_json = None
    audit_id = await insert_audit(
        db,
        actor=actor,
        action=JOB_REQUEUE_ACTION,
        target_type="job",
        target_id=job_id,
        payload={
            "reason": sanitized_reason(reason),
            "force": bool(force),
            "previousStatus": previous_status,
            "newStatus": job.status,
            "noOp": no_op,
            "staleRunning": stale_running,
            "staleRunningThresholdSeconds": job_stale_seconds(),
        },
    )
    await db.commit()
    log_admin_action(
        audit_id=audit_id,
        action=JOB_REQUEUE_ACTION,
        target_type="job",
        target_id=job_id,
        actor_id=actor.actor_id,
    )
    return JobRequeueResult(
        job_id=job.id,
        previous_status=previous_status,
        new_status=job.status,
        audit_id=audit_id,
    )


__all__ = ["requeue_job"]
