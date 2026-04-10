"""Application module for trials services trials lifecycle actions service workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
)
from app.trials.services.trials_services_trials_lifecycle_access_service import (
    require_owner_for_lifecycle,
)
from app.trials.services.trials_services_trials_lifecycle_transition_rules_service import (
    apply_status_transition,
)


async def _transition_owned_trial_impl(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
    target_status: str,
    now: datetime | None = None,
    require_owner: Callable[..., object] = require_owner_for_lifecycle,
    apply_transition: Callable[..., bool] = apply_status_transition,
    normalize_status: Callable[..., str | None],
    logger: logging.Logger,
) -> Trial:
    changed_at = now or datetime.now(UTC)
    trial = await require_owner(db, trial_id, actor_user_id, for_update=True)
    from_status = normalize_status(trial.status)
    pending_scenario_version_id = getattr(trial, "pending_scenario_version_id", None)
    if (
        target_status == TRIAL_STATUS_ACTIVE_INVITING
        and pending_scenario_version_id is not None
    ):
        raise ApiError(
            status_code=409,
            detail="Scenario approval is pending before inviting.",
            error_code="SCENARIO_APPROVAL_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": pending_scenario_version_id},
        )
    try:
        changed = apply_transition(
            trial, target_status=target_status, changed_at=changed_at
        )
    except ApiError:
        logger.warning(
            "Rejected trial transition trialId=%s actorUserId=%s from=%s to=%s",
            trial_id,
            actor_user_id,
            from_status,
            target_status,
        )
        raise
    await db.commit()
    await db.refresh(trial)
    if changed:
        logger.info(
            "Trial transition trialId=%s actorUserId=%s from=%s to=%s",
            trial.id,
            actor_user_id,
            from_status,
            normalize_status(trial.status),
        )
    else:
        logger.info(
            "Trial transition idempotent trialId=%s actorUserId=%s status=%s",
            trial.id,
            actor_user_id,
            normalize_status(trial.status),
        )
    return trial


__all__ = ["_transition_owned_trial_impl"]
