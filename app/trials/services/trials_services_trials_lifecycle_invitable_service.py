"""Application module for trials services trials lifecycle invitable service workflows."""

from __future__ import annotations

from fastapi import status

from app.shared.database.shared_database_models_model import Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
    TRIAL_STATUS_TERMINATED,
)
from app.trials.services.trials_services_trials_lifecycle_status_service import (
    normalize_trial_status,
)


def require_trial_invitable(trial: Trial) -> None:
    """Require trial invitable."""
    current_status = normalize_trial_status(trial.status)
    if current_status == TRIAL_STATUS_TERMINATED:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trial has been terminated.",
            error_code="TRIAL_TERMINATED",
            retryable=False,
            details={"status": current_status},
        )
    pending_scenario_version_id = getattr(trial, "pending_scenario_version_id", None)
    if pending_scenario_version_id is not None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario approval is pending before inviting.",
            error_code="SCENARIO_APPROVAL_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": pending_scenario_version_id},
        )
    if current_status != TRIAL_STATUS_ACTIVE_INVITING:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trial is not approved for inviting.",
            error_code="TRIAL_NOT_INVITABLE",
            retryable=False,
            details={"status": current_status},
        )


__all__ = ["require_trial_invitable"]
