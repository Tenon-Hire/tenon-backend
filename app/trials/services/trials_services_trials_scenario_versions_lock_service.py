"""Application module for trials services trials scenario versions lock service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import ScenarioVersion, Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.trials.services.trials_services_trials_scenario_versions_access_service import (
    get_active_scenario_for_update,
)

logger = logging.getLogger(__name__)


async def lock_active_scenario_for_invites(
    db: AsyncSession,
    *,
    trial_id: int,
    now: datetime | None = None,
    trial: Trial | None = None,
) -> ScenarioVersion:
    """Execute lock active scenario for invites."""
    lock_at = now or datetime.now(UTC)
    locked_trial = trial
    if locked_trial is None:
        locked_trial = (
            await db.execute(
                select(Trial).where(Trial.id == trial_id).with_for_update()
            )
        ).scalar_one_or_none()
        if locked_trial is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found"
            )
    active = await get_active_scenario_for_update(db, locked_trial)
    if active.status == SCENARIO_VERSION_STATUS_LOCKED:
        return active
    if active.status != SCENARIO_VERSION_STATUS_READY:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not approved for inviting.",
            error_code="SCENARIO_NOT_READY",
            retryable=False,
            details={"status": active.status},
        )
    active.status = SCENARIO_VERSION_STATUS_LOCKED
    active.locked_at = lock_at
    logger.info(
        "Scenario version locked trialId=%s scenarioVersionId=%s lockedAt=%s",
        locked_trial.id,
        active.id,
        active.locked_at.isoformat() if active.locked_at else None,
    )
    return active
