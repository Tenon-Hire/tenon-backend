"""Application module for integrations github webhooks handlers workflow run jobs handler workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_models_handler import (
    GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
    WorkflowRunCompletedEvent,
)
from app.shared.database.shared_database_models_model import Job, Submission
from app.shared.jobs.repositories import repository as jobs_repo


def build_artifact_parse_job_idempotency_key(
    *, submission_id: int, workflow_run_id: int, workflow_run_attempt: int | None
) -> str:
    """Build artifact parse job idempotency key."""
    attempt = workflow_run_attempt or 1
    return f"github_workflow_artifact_parse:{submission_id}:{workflow_run_id}:{attempt}"


async def enqueue_artifact_parse_job(
    db: AsyncSession,
    *,
    submission: Submission,
    company_id: int,
    event: WorkflowRunCompletedEvent,
    delivery_id: str | None,
) -> bool:
    """Enqueue artifact parse job."""
    idempotency_key = build_artifact_parse_job_idempotency_key(
        submission_id=submission.id,
        workflow_run_id=event.workflow_run_id,
        workflow_run_attempt=event.run_attempt,
    )
    existing = (
        await db.execute(
            select(Job.id).where(
                Job.company_id == company_id,
                Job.job_type == GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
                Job.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()
    payload_json = {
        "submissionId": submission.id,
        "candidateSessionId": submission.candidate_session_id,
        "taskId": submission.task_id,
        "repoFullName": event.repo_full_name,
        "workflowRunId": event.workflow_run_id,
        "workflowRunAttempt": event.run_attempt,
        "workflowCompletedAt": event.completed_at.isoformat().replace("+00:00", "Z")
        if event.completed_at is not None
        else None,
        "githubDeliveryId": delivery_id,
    }
    await jobs_repo.create_or_get_idempotent(
        db,
        job_type=GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
        idempotency_key=idempotency_key,
        payload_json=payload_json,
        company_id=company_id,
        candidate_session_id=submission.candidate_session_id,
        correlation_id=f"github_workflow_run:{event.workflow_run_id}",
        commit=False,
    )
    return existing is None


__all__ = ["build_artifact_parse_job_idempotency_key", "enqueue_artifact_parse_job"]
