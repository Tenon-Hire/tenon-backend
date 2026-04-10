"""Application module for trials services trials lifecycle service workflows."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    ScenarioVersion,
    Task,
    Trial,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
)
from app.trials.services.trials_services_trials_codespace_specializer_service import (
    ensure_precommit_bundle_prepared_for_approved_scenario,
)
from app.trials.services.trials_services_trials_lifecycle_access_service import (
    require_owner_for_lifecycle,
)
from app.trials.services.trials_services_trials_lifecycle_actions_service import (
    _transition_owned_trial_impl,
)
from app.trials.services.trials_services_trials_lifecycle_invitable_service import (
    require_trial_invitable,
)
from app.trials.services.trials_services_trials_lifecycle_status_service import (
    normalize_trial_status,
    normalize_trial_status_or_raise,
)
from app.trials.services.trials_services_trials_lifecycle_termination_service import (
    TerminateTrialResult,
    terminate_trial_with_cleanup_impl,
)
from app.trials.services.trials_services_trials_lifecycle_transition_rules_service import (
    apply_status_transition,
)
from app.trials.services.trials_services_trials_scenario_versions_create_service import (
    get_active_scenario_version,
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


async def _prepare_active_scenario_bundle_on_activation(
    db: AsyncSession,
    *,
    trial: Trial,
) -> ScenarioVersion | None:
    active_scenario_version = await get_active_scenario_version(db, trial.id)
    if active_scenario_version is None:
        return None
    tasks = await _load_trial_tasks(db, trial.id)
    await ensure_precommit_bundle_prepared_for_approved_scenario(
        db,
        trial=trial,
        scenario_version=active_scenario_version,
        tasks=tasks,
    )
    await db.commit()
    return active_scenario_version


async def activate_trial(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
    now: datetime | None = None,
) -> Trial:
    """Activate trial."""
    trial = await _transition_owned_trial_impl(
        db,
        trial_id=trial_id,
        actor_user_id=actor_user_id,
        target_status=TRIAL_STATUS_ACTIVE_INVITING,
        now=now,
        require_owner=require_owner_for_lifecycle,
        apply_transition=apply_status_transition,
        normalize_status=normalize_trial_status,
        logger=logger,
    )
    await _prepare_active_scenario_bundle_on_activation(db, trial=trial)
    await db.refresh(trial)
    return trial


async def terminate_trial(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
) -> Trial:
    """Terminate trial."""
    return (
        await terminate_trial_with_cleanup(
            db,
            trial_id=trial_id,
            actor_user_id=actor_user_id,
            reason=reason,
            now=now,
        )
    ).trial


async def terminate_trial_with_cleanup(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
) -> TerminateTrialResult:
    """Terminate trial with cleanup."""
    return await terminate_trial_with_cleanup_impl(
        db,
        trial_id=trial_id,
        actor_user_id=actor_user_id,
        reason=reason,
        now=now,
        require_owner=require_owner_for_lifecycle,
        apply_transition=apply_status_transition,
        normalize_status=normalize_trial_status,
        logger=logger,
    )


__all__ = [
    "TerminateTrialResult",
    "activate_trial",
    "apply_status_transition",
    "normalize_trial_status",
    "normalize_trial_status_or_raise",
    "require_owner_for_lifecycle",
    "require_trial_invitable",
    "terminate_trial",
    "terminate_trial_with_cleanup",
]
