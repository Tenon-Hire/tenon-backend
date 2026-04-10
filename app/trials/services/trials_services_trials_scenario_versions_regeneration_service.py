"""Application module for trials services trials scenario versions regeneration service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    Job,
    ScenarioVersion,
    Trial,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_READY_FOR_REVIEW,
)
from app.trials.services.trials_services_trials_lifecycle_service import (
    apply_status_transition,
)
from app.trials.services.trials_services_trials_scenario_versions_access_service import (
    get_active_scenario_for_update,
    require_owned_trial_for_update,
)
from app.trials.services.trials_services_trials_scenario_versions_regeneration_helpers_service import (
    clone_pending_scenario,
    enqueue_regeneration_job,
)

logger = logging.getLogger(__name__)


async def regenerate_active_scenario_version(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
) -> tuple[Trial, ScenarioVersion]:
    """Regenerate active scenario version."""
    trial, regenerated, _job = await request_scenario_regeneration(
        db, trial_id=trial_id, actor_user_id=actor_user_id
    )
    return trial, regenerated


async def request_scenario_regeneration(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
) -> tuple[Trial, ScenarioVersion, Job]:
    """Execute request scenario regeneration."""
    regenerated_at = datetime.now(UTC)
    trial = await require_owned_trial_for_update(db, trial_id, actor_user_id)
    if trial.pending_scenario_version_id is not None:
        raise ApiError(
            status_code=409,
            detail="Scenario regeneration is already pending approval.",
            error_code="SCENARIO_REGENERATION_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": trial.pending_scenario_version_id},
        )
    active = await get_active_scenario_for_update(db, trial)
    new_index = await scenario_repo.next_version_index(db, trial.id)
    regenerated = clone_pending_scenario(trial, active, new_index)
    db.add(regenerated)
    await db.flush()
    trial.pending_scenario_version_id = regenerated.id
    apply_status_transition(
        trial,
        target_status=TRIAL_STATUS_READY_FOR_REVIEW,
        changed_at=regenerated_at,
    )
    scenario_job = await enqueue_regeneration_job(db, trial, regenerated)
    await db.commit()
    await db.refresh(trial)
    await db.refresh(regenerated)
    await db.refresh(scenario_job)
    logger.info(
        "Scenario regeneration requested trialId=%s fromScenarioVersionId=%s toScenarioVersionId=%s versionIndex=%s jobId=%s",
        trial.id,
        active.id,
        regenerated.id,
        regenerated.version_index,
        scenario_job.id,
    )
    return trial, regenerated, scenario_job
