"""Application module for Talent Partners services Talent Partners admin ops trial helpers service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import ScenarioVersion, Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_audit_service import (
    unsafe_operation,
)
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)


async def load_trial_for_update(db: AsyncSession, trial_id: int) -> Trial:
    """Load trial for update."""
    trial = (
        await db.execute(select(Trial).where(Trial.id == trial_id).with_for_update())
    ).scalar_one_or_none()
    if trial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trial not found",
        )
    return trial


async def load_scenario_version_for_update(
    db: AsyncSession, scenario_version_id: int
) -> ScenarioVersion:
    """Load scenario version for update."""
    scenario_version = (
        await db.execute(
            select(ScenarioVersion)
            .where(ScenarioVersion.id == scenario_version_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if scenario_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario version not found",
        )
    return scenario_version


def assert_fallback_eligible(
    *,
    trial: Trial,
    scenario_version: ScenarioVersion,
    trial_id: int,
    scenario_version_id: int,
) -> None:
    """Assert fallback eligible."""
    if trial.status == TRIAL_STATUS_TERMINATED:
        unsafe_operation(
            "Cannot switch fallback scenario for a terminated trial.",
            details={"trialId": trial_id, "status": trial.status},
        )
    if scenario_version.trial_id != trial.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario version not found",
        )
    if scenario_version.status not in {
        SCENARIO_VERSION_STATUS_READY,
        SCENARIO_VERSION_STATUS_LOCKED,
    }:
        unsafe_operation(
            "Scenario version is not eligible as a fallback.",
            details={
                "trialId": trial_id,
                "scenarioVersionId": scenario_version_id,
                "status": scenario_version.status,
            },
        )
    if trial.pending_scenario_version_id is not None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario approval is pending before inviting.",
            error_code="SCENARIO_APPROVAL_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": trial.pending_scenario_version_id},
        )


__all__ = [
    "assert_fallback_eligible",
    "load_scenario_version_for_update",
    "load_trial_for_update",
]
