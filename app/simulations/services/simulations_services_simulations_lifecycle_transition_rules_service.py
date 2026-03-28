"""Application module for simulations services simulations lifecycle transition rules service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import status

from app.shared.database.shared_database_models_model import Simulation
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_TERMINATED,
    SIMULATION_STATUSES,
)
from app.simulations.services.simulations_services_simulations_lifecycle_status_service import (
    _ALLOWED_TRANSITIONS,
    _allowed_targets,
    normalize_simulation_status,
)


def _touch_timestamp(simulation: Simulation, target_status: str, at: datetime) -> None:
    if (
        target_status == SIMULATION_STATUS_GENERATING
        and simulation.generating_at is None
    ):
        simulation.generating_at = at
        return
    if (
        target_status == SIMULATION_STATUS_READY_FOR_REVIEW
        and simulation.ready_for_review_at is None
    ):
        simulation.ready_for_review_at = at
        return
    if (
        target_status == SIMULATION_STATUS_ACTIVE_INVITING
        and simulation.activated_at is None
    ):
        simulation.activated_at = at
        return
    if (
        target_status == SIMULATION_STATUS_TERMINATED
        and simulation.terminated_at is None
    ):
        simulation.terminated_at = at


def _raise_invalid_transition(current_status: str | None, target_status: str) -> None:
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Simulation status transition is not allowed.",
        error_code="SIMULATION_INVALID_STATUS_TRANSITION",
        retryable=False,
        details={
            "status": normalize_simulation_status(current_status),
            "targetStatus": target_status,
            "allowedTransitions": _allowed_targets(current_status),
        },
    )


def apply_status_transition(
    simulation: Simulation,
    *,
    target_status: str,
    changed_at: datetime | None = None,
) -> bool:
    """Apply status transition."""
    changed_at = changed_at or datetime.now(UTC)
    current_status = normalize_simulation_status(simulation.status)
    target_status = normalize_simulation_status(target_status)
    if target_status not in SIMULATION_STATUSES:
        raise ValueError(f"Unsupported simulation status: {target_status}")
    if current_status == target_status:
        simulation.status = target_status
        _touch_timestamp(simulation, target_status, changed_at)
        return False
    if target_status == SIMULATION_STATUS_TERMINATED:
        if current_status not in SIMULATION_STATUSES:
            _raise_invalid_transition(current_status, target_status)
    elif target_status not in _ALLOWED_TRANSITIONS.get(current_status or "", set()):
        _raise_invalid_transition(current_status, target_status)
    simulation.status = target_status
    _touch_timestamp(simulation, target_status, changed_at)
    return True


__all__ = ["apply_status_transition"]
