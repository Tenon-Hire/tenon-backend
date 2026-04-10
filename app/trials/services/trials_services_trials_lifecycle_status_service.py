"""Application module for trials services trials lifecycle status service workflows."""

from __future__ import annotations

from fastapi import status

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.trials_repositories_trials_trial_model import (
    LEGACY_TRIAL_STATUS_ACTIVE,
    TRIAL_STATUS_ACTIVE_INVITING,
    TRIAL_STATUS_DRAFT,
    TRIAL_STATUS_GENERATING,
    TRIAL_STATUS_READY_FOR_REVIEW,
    TRIAL_STATUS_TERMINATED,
    TRIAL_STATUSES,
)

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    TRIAL_STATUS_DRAFT: {TRIAL_STATUS_GENERATING},
    TRIAL_STATUS_GENERATING: {TRIAL_STATUS_READY_FOR_REVIEW},
    TRIAL_STATUS_READY_FOR_REVIEW: {TRIAL_STATUS_ACTIVE_INVITING},
    TRIAL_STATUS_ACTIVE_INVITING: {TRIAL_STATUS_READY_FOR_REVIEW},
    TRIAL_STATUS_TERMINATED: set(),
}


def normalize_trial_status(raw_status: str | None) -> str | None:
    """Normalize trial status."""
    if raw_status == LEGACY_TRIAL_STATUS_ACTIVE:
        return TRIAL_STATUS_ACTIVE_INVITING
    if raw_status in TRIAL_STATUSES:
        return raw_status
    return None


def normalize_trial_status_or_raise(raw_status: str | None) -> str:
    """Normalize trial status or raise."""
    normalized = normalize_trial_status(raw_status)
    if normalized is not None:
        return normalized
    raise ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Invalid trial status.",
        error_code="TRIAL_STATUS_INVALID",
        retryable=False,
        details={"status": raw_status},
    )


def _allowed_targets(current_status: str | None) -> list[str]:
    normalized = normalize_trial_status(current_status)
    return sorted(_ALLOWED_TRANSITIONS.get(normalized or "", set()))


__all__ = [
    "_ALLOWED_TRANSITIONS",
    "_allowed_targets",
    "normalize_trial_status",
    "normalize_trial_status_or_raise",
]
