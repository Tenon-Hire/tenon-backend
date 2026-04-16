"""Application module for trials services trials lifecycle termination service workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Job,
    Trial,
)
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)
from app.trials.services.trials_services_trials_cleanup_jobs_service import (
    TRIAL_CLEANUP_JOB_TYPE,
    enqueue_trial_cleanup_job,
)
from app.trials.services.trials_services_trials_lifecycle_access_service import (
    require_owner_for_lifecycle,
)
from app.trials.services.trials_services_trials_lifecycle_transition_rules_service import (
    apply_status_transition,
)


@dataclass(slots=True)
class TerminateTrialResult:
    """Represent terminate trial result data and behavior."""

    trial: Trial
    cleanup_job_ids: list[str]


async def _expire_pending_candidate_sessions(
    db: AsyncSession, *, trial_id: int, changed_at: datetime
) -> int:
    """Expire pending invite rows for the terminated trial."""
    result = await db.execute(
        select(CandidateSession).where(
            CandidateSession.trial_id == trial_id,
            CandidateSession.status == "not_started",
            CandidateSession.started_at.is_(None),
        )
    )
    expired = 0
    for candidate_session in result.scalars():
        candidate_session.status = "expired"
        candidate_session.expires_at = changed_at
        expired += 1
    return expired


async def _cancel_pending_trial_jobs(
    db: AsyncSession,
    *,
    trial: Trial,
    changed_at: datetime,
) -> int:
    """Cancel pending jobs scoped to the terminated trial."""
    candidate_session_ids = select(CandidateSession.id).where(
        CandidateSession.trial_id == trial.id
    )
    result = await db.execute(
        select(Job).where(
            Job.company_id == trial.company_id,
            Job.job_type != TRIAL_CLEANUP_JOB_TYPE,
            Job.status.in_((JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)),
            or_(
                Job.candidate_session_id.in_(candidate_session_ids),
                Job.payload_json["trialId"].as_integer() == trial.id,
                Job.correlation_id.like(f"trial:{trial.id}%"),
            ),
        )
    )
    cancelled = 0
    for job in result.scalars():
        job.status = JOB_STATUS_DEAD_LETTER
        job.last_error = "trial_terminated"
        job.result_json = None
        job.locked_at = None
        job.locked_by = None
        job.next_run_at = None
        job.updated_at = changed_at
        cancelled += 1
    return cancelled


async def terminate_trial_with_cleanup_impl(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
    require_owner: Callable[..., object] = require_owner_for_lifecycle,
    apply_transition: Callable[..., bool] = apply_status_transition,
    enqueue_cleanup_job: Callable[..., object] = enqueue_trial_cleanup_job,
    normalize_status: Callable[..., str | None],
    logger: logging.Logger,
) -> TerminateTrialResult:
    """Terminate trial with cleanup impl."""
    changed_at = now or datetime.now(UTC)
    normalized_reason = (reason or "").strip() or None
    trial = await require_owner(db, trial_id, actor_user_id, for_update=True)
    from_status = normalize_status(trial.status)
    try:
        changed = apply_transition(
            trial,
            target_status=TRIAL_STATUS_TERMINATED,
            changed_at=changed_at,
        )
    except ApiError:
        logger.warning(
            "Rejected trial termination trialId=%s actorUserId=%s from=%s",
            trial_id,
            actor_user_id,
            from_status,
        )
        raise
    if changed:
        trial.terminated_by_talent_partner_id = actor_user_id
    if normalized_reason is not None and trial.terminated_reason is None:
        trial.terminated_reason = normalized_reason
    expired_count = await _expire_pending_candidate_sessions(
        db, trial_id=trial.id, changed_at=changed_at
    )
    cancelled_job_count = await _cancel_pending_trial_jobs(
        db, trial=trial, changed_at=changed_at
    )
    cleanup_job = await enqueue_cleanup_job(
        db,
        trial=trial,
        terminated_by_user_id=actor_user_id,
        reason=normalized_reason,
        commit=False,
    )
    await db.commit()
    await db.refresh(trial)
    cleanup_job_ids = [str(cleanup_job.id)]
    logger.info(
        (
            "Trial terminated trialId=%s actorUserId=%s from=%s to=%s "
            "expiredInvites=%s cancelledJobs=%s cleanupJobIds=%s"
        ),
        trial.id,
        actor_user_id,
        from_status,
        normalize_status(trial.status),
        expired_count,
        cancelled_job_count,
        cleanup_job_ids,
    )
    return TerminateTrialResult(trial=trial, cleanup_job_ids=cleanup_job_ids)


__all__ = ["TerminateTrialResult", "terminate_trial_with_cleanup_impl"]
