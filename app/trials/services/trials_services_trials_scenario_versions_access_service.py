"""Application module for trials services trials scenario versions access service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import ScenarioVersion, Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)


async def require_owned_trial_for_update(
    db: AsyncSession, trial_id: int, actor_user_id: int
) -> Trial:
    """Require owned trial for update."""
    stmt = select(Trial).where(Trial.id == trial_id).with_for_update()
    trial = (await db.execute(stmt)).scalar_one_or_none()
    if trial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found"
        )
    if trial.created_by != actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trial",
        )
    return trial


def scenario_generation_idempotency_key(scenario_version_id: int) -> str:
    """Execute scenario generation idempotency key."""
    return f"scenario_version:{scenario_version_id}:scenario_generation"


def raise_active_scenario_missing() -> None:
    """Execute raise active scenario missing."""
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Trial has no active scenario version.",
        error_code="SCENARIO_ACTIVE_VERSION_MISSING",
        retryable=False,
        details={},
    )


async def get_active_scenario_for_update(
    db: AsyncSession, trial: Trial
) -> ScenarioVersion:
    """Return active scenario for update."""
    active_scenario_version_id = trial.active_scenario_version_id
    if active_scenario_version_id is None:
        raise_active_scenario_missing()
    active = await scenario_repo.get_by_id(
        db, active_scenario_version_id, for_update=True
    )
    if active is None or active.trial_id != trial.id:
        raise_active_scenario_missing()
    return active
