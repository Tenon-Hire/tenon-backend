"""Application module for trials services trials scenario versions approval service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    ScenarioVersion,
    Task,
    Trial,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_READY,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
)
from app.trials.services.trials_services_trials_codespace_specializer_service import (
    ensure_precommit_bundle_prepared_for_approved_scenario,
)
from app.trials.services.trials_services_trials_lifecycle_service import (
    apply_status_transition,
)
from app.trials.services.trials_services_trials_scenario_versions_access_service import (
    require_owned_trial_for_update,
)

logger = logging.getLogger(__name__)


async def _load_trial_tasks(db: AsyncSession, trial_id: int) -> list[Task]:
    return (
        (
            await db.execute(
                select(Task)
                .where(Task.trial_id == trial_id)
                .order_by(Task.day_index.asc())
            )
        )
        .scalars()
        .all()
    )


async def approve_scenario_version(
    db: AsyncSession,
    *,
    trial_id: int,
    scenario_version_id: int,
    actor_user_id: int,
    now: datetime | None = None,
) -> tuple[Trial, ScenarioVersion]:
    """Approve scenario version."""
    approved_at = now or datetime.now(UTC)
    trial = await require_owned_trial_for_update(db, trial_id, actor_user_id)
    target = await scenario_repo.get_by_id(db, scenario_version_id, for_update=True)
    if target is None or target.trial_id != trial.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scenario version not found"
        )
    pending_id = trial.pending_scenario_version_id
    if pending_id is None:
        return await _approve_without_pending(db, trial, target, approved_at)
    if pending_id != target.id:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not pending approval.",
            error_code="SCENARIO_VERSION_NOT_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": pending_id},
        )
    if target.status != SCENARIO_VERSION_STATUS_READY:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not ready for approval.",
            error_code="SCENARIO_NOT_READY",
            retryable=False,
            details={"status": target.status},
        )
    trial.active_scenario_version_id = target.id
    trial.pending_scenario_version_id = None
    apply_status_transition(
        trial,
        target_status=TRIAL_STATUS_ACTIVE_INVITING,
        changed_at=approved_at,
    )
    tasks = await _load_trial_tasks(db, trial.id)
    await ensure_precommit_bundle_prepared_for_approved_scenario(
        db,
        trial=trial,
        scenario_version=target,
        tasks=tasks,
    )
    await db.commit()
    await db.refresh(trial)
    await db.refresh(target)
    logger.info(
        "Scenario version approved trialId=%s actorUserId=%s scenarioVersionId=%s status=%s",
        trial.id,
        actor_user_id,
        target.id,
        trial.status,
    )
    return trial, target


async def _approve_without_pending(
    db: AsyncSession,
    trial: Trial,
    target: ScenarioVersion,
    approved_at: datetime,
) -> tuple[Trial, ScenarioVersion]:
    if trial.active_scenario_version_id != target.id:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="No pending scenario version to approve.",
            error_code="SCENARIO_APPROVAL_NOT_PENDING",
            retryable=False,
            details={},
        )
    apply_status_transition(
        trial,
        target_status=TRIAL_STATUS_ACTIVE_INVITING,
        changed_at=approved_at,
    )
    tasks = await _load_trial_tasks(db, trial.id)
    await ensure_precommit_bundle_prepared_for_approved_scenario(
        db,
        trial=trial,
        scenario_version=target,
        tasks=tasks,
    )
    await db.commit()
    await db.refresh(trial)
    await db.refresh(target)
    return trial, target
