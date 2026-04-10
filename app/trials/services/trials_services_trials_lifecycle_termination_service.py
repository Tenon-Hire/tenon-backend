"""Application module for trials services trials lifecycle termination service workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)
from app.trials.services.trials_services_trials_cleanup_jobs_service import (
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
        if normalized_reason is not None:
            trial.terminated_reason = normalized_reason
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
        "Trial terminated trialId=%s actorUserId=%s from=%s to=%s cleanupJobIds=%s",
        trial.id,
        actor_user_id,
        from_status,
        normalize_status(trial.status),
        cleanup_job_ids,
    )
    return TerminateTrialResult(trial=trial, cleanup_job_ids=cleanup_job_ids)


__all__ = ["TerminateTrialResult", "terminate_trial_with_cleanup_impl"]
