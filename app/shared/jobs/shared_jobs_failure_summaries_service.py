"""Safe durable job failure summaries."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import CandidateSession, Job
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
)
from app.shared.jobs.shared_jobs_failure_reasons_service import (
    failure_category,
    human_failure_reason,
)
from app.shared.types.shared_types_base_model import APIModel

_TRIAL_CORRELATION_RE = re.compile(r"(?:^|:)trial:(\d+)(?:$|:)")


class SafeFailedJobSummary(APIModel):
    """Operator-safe failed job metadata."""

    jobId: str
    jobType: str
    status: str
    queueName: str | None = None
    workerName: str | None = None
    trialId: int | None = None
    candidateSessionId: int | None = None
    attempts: int
    maxAttempts: int
    createdAt: datetime
    updatedAt: datetime
    failedAt: datetime | None = None
    nextRetryAt: datetime | None = None
    failureReason: str
    failureCode: str


class FailedJobsListResponse(APIModel):
    """Paginated failed jobs response."""

    items: list[SafeFailedJobSummary]
    limit: int
    offset: int
    total: int


class TrialLatestFailureSummary(APIModel):
    """Safe Trial detail failure summary."""

    jobId: str
    jobType: str
    failedAt: datetime | None = None
    reason: str


class TrialBackgroundFailures(APIModel):
    """Safe background failure state for a Trial detail response."""

    hasFailedJobs: bool
    failedJobsCount: int
    latestFailure: TrialLatestFailureSummary | None = None


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def trial_id_from_job(job: Job, candidate_trial_id: int | None = None) -> int | None:
    """Infer a related Trial id from durable job metadata."""
    if candidate_trial_id is not None:
        return candidate_trial_id
    payload = job.payload_json if isinstance(job.payload_json, dict) else {}
    for key in ("trialId", "trial_id"):
        parsed = _positive_int(payload.get(key))
        if parsed is not None:
            return parsed
    correlation_id = getattr(job, "correlation_id", None) or ""
    match = _TRIAL_CORRELATION_RE.search(correlation_id)
    if match:
        return _positive_int(match.group(1))
    return None


def safe_failed_job_summary(
    job: Job, *, candidate_trial_id: int | None = None
) -> SafeFailedJobSummary:
    """Render a failed job without stack traces, secrets, or raw payloads."""
    reason = human_failure_reason(job_type=job.job_type, error=job.last_error)
    return SafeFailedJobSummary(
        jobId=job.id,
        jobType=job.job_type,
        status=job.status,
        queueName=None,
        workerName=job.locked_by,
        trialId=trial_id_from_job(job, candidate_trial_id),
        candidateSessionId=job.candidate_session_id,
        attempts=job.attempt,
        maxAttempts=job.max_attempts,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
        failedAt=job.updated_at if job.status == JOB_STATUS_DEAD_LETTER else None,
        nextRetryAt=job.next_run_at,
        failureReason=reason,
        failureCode=failure_category(job.last_error),
    )


async def list_failed_jobs(
    db: AsyncSession, *, limit: int = 50, offset: int = 0
) -> FailedJobsListResponse:
    """List failed durable jobs for operators."""
    total = int(
        await db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.status == JOB_STATUS_DEAD_LETTER)
        )
        or 0
    )
    rows = (
        await db.execute(
            select(Job, CandidateSession.trial_id)
            .outerjoin(
                CandidateSession, CandidateSession.id == Job.candidate_session_id
            )
            .where(Job.status == JOB_STATUS_DEAD_LETTER)
            .order_by(Job.updated_at.desc(), Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return FailedJobsListResponse(
        items=[
            safe_failed_job_summary(job, candidate_trial_id=candidate_trial_id)
            for job, candidate_trial_id in rows
        ],
        limit=limit,
        offset=offset,
        total=total,
    )


def _trial_failed_jobs_filter(trial_id: int):
    return or_(
        CandidateSession.trial_id == trial_id,
        Job.correlation_id == f"trial:{trial_id}",
        Job.correlation_id.like(f"trial:{trial_id}:%"),
        Job.payload_json["trialId"].as_integer() == trial_id,
        Job.payload_json["trial_id"].as_integer() == trial_id,
    )


async def trial_background_failures(
    db: AsyncSession, *, trial_id: int, company_id: int
) -> TrialBackgroundFailures:
    """Return failed background job state scoped to one Trial."""
    base_filter = (
        Job.company_id == company_id,
        Job.status == JOB_STATUS_DEAD_LETTER,
        _trial_failed_jobs_filter(trial_id),
    )
    total = int(
        await db.scalar(
            select(func.count())
            .select_from(Job)
            .outerjoin(
                CandidateSession, CandidateSession.id == Job.candidate_session_id
            )
            .where(*base_filter)
        )
        or 0
    )
    latest_row = (
        await db.execute(
            select(Job, CandidateSession.trial_id)
            .outerjoin(
                CandidateSession, CandidateSession.id == Job.candidate_session_id
            )
            .where(*base_filter)
            .order_by(Job.updated_at.desc(), Job.created_at.desc())
            .limit(1)
        )
    ).first()
    if latest_row is None:
        return TrialBackgroundFailures(
            hasFailedJobs=False,
            failedJobsCount=0,
            latestFailure=None,
        )
    latest = safe_failed_job_summary(latest_row[0], candidate_trial_id=latest_row[1])
    return TrialBackgroundFailures(
        hasFailedJobs=True,
        failedJobsCount=total,
        latestFailure=TrialLatestFailureSummary(
            jobId=latest.jobId,
            jobType=latest.jobType,
            failedAt=latest.failedAt,
            reason=latest.failureReason,
        ),
    )


__all__ = [
    "FailedJobsListResponse",
    "SafeFailedJobSummary",
    "TrialBackgroundFailures",
    "TrialLatestFailureSummary",
    "list_failed_jobs",
    "safe_failed_job_summary",
    "trial_background_failures",
    "trial_id_from_job",
]
