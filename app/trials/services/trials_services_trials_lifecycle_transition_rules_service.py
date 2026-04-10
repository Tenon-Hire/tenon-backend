"""Application module for trials services trials lifecycle transition rules service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import status

from app.shared.database.shared_database_models_model import Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
    TRIAL_STATUS_GENERATING,
    TRIAL_STATUS_READY_FOR_REVIEW,
    TRIAL_STATUS_TERMINATED,
    TRIAL_STATUSES,
)
from app.trials.services.trials_services_trials_lifecycle_status_service import (
    _ALLOWED_TRANSITIONS,
    _allowed_targets,
    normalize_trial_status,
)


def _touch_timestamp(trial: Trial, target_status: str, at: datetime) -> None:
    if target_status == TRIAL_STATUS_GENERATING and trial.generating_at is None:
        trial.generating_at = at
        return
    if (
        target_status == TRIAL_STATUS_READY_FOR_REVIEW
        and trial.ready_for_review_at is None
    ):
        trial.ready_for_review_at = at
        return
    if target_status == TRIAL_STATUS_ACTIVE_INVITING and trial.activated_at is None:
        trial.activated_at = at
        return
    if target_status == TRIAL_STATUS_TERMINATED and trial.terminated_at is None:
        trial.terminated_at = at


def _raise_invalid_transition(current_status: str | None, target_status: str) -> None:
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Trial status transition is not allowed.",
        error_code="TRIAL_INVALID_STATUS_TRANSITION",
        retryable=False,
        details={
            "status": normalize_trial_status(current_status),
            "targetStatus": target_status,
            "allowedTransitions": _allowed_targets(current_status),
        },
    )


def apply_status_transition(
    trial: Trial,
    *,
    target_status: str,
    changed_at: datetime | None = None,
) -> bool:
    """Apply status transition."""
    changed_at = changed_at or datetime.now(UTC)
    current_status = normalize_trial_status(trial.status)
    target_status = normalize_trial_status(target_status)
    if target_status not in TRIAL_STATUSES:
        raise ValueError(f"Unsupported trial status: {target_status}")
    if current_status == target_status:
        trial.status = target_status
        _touch_timestamp(trial, target_status, changed_at)
        return False
    if target_status == TRIAL_STATUS_TERMINATED:
        if current_status not in TRIAL_STATUSES:
            _raise_invalid_transition(current_status, target_status)
    elif target_status not in _ALLOWED_TRANSITIONS.get(current_status or "", set()):
        _raise_invalid_transition(current_status, target_status)
    trial.status = target_status
    _touch_timestamp(trial, target_status, changed_at)
    return True


__all__ = ["apply_status_transition"]
