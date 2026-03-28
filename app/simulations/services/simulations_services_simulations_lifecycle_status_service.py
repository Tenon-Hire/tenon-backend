"""Application module for simulations services simulations lifecycle status service workflows."""

from __future__ import annotations

from fastapi import status

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    LEGACY_SIMULATION_STATUS_ACTIVE,
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_DRAFT,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_TERMINATED,
    SIMULATION_STATUSES,
)

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    SIMULATION_STATUS_DRAFT: {SIMULATION_STATUS_GENERATING},
    SIMULATION_STATUS_GENERATING: {SIMULATION_STATUS_READY_FOR_REVIEW},
    SIMULATION_STATUS_READY_FOR_REVIEW: {SIMULATION_STATUS_ACTIVE_INVITING},
    SIMULATION_STATUS_ACTIVE_INVITING: {SIMULATION_STATUS_READY_FOR_REVIEW},
    SIMULATION_STATUS_TERMINATED: set(),
}


def normalize_simulation_status(raw_status: str | None) -> str | None:
    """Normalize simulation status."""
    if raw_status == LEGACY_SIMULATION_STATUS_ACTIVE:
        return SIMULATION_STATUS_ACTIVE_INVITING
    if raw_status in SIMULATION_STATUSES:
        return raw_status
    return None


def normalize_simulation_status_or_raise(raw_status: str | None) -> str:
    """Normalize simulation status or raise."""
    normalized = normalize_simulation_status(raw_status)
    if normalized is not None:
        return normalized
    raise ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Invalid simulation status.",
        error_code="SIMULATION_STATUS_INVALID",
        retryable=False,
        details={"status": raw_status},
    )


def _allowed_targets(current_status: str | None) -> list[str]:
    normalized = normalize_simulation_status(current_status)
    return sorted(_ALLOWED_TRANSITIONS.get(normalized or "", set()))


__all__ = [
    "_ALLOWED_TRANSITIONS",
    "_allowed_targets",
    "normalize_simulation_status",
    "normalize_simulation_status_or_raise",
]
