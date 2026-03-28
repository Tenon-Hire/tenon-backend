"""Application module for simulations services simulations lifecycle invitable service workflows."""

from __future__ import annotations

from fastapi import status

from app.shared.database.shared_database_models_model import Simulation
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_TERMINATED,
)
from app.simulations.services.simulations_services_simulations_lifecycle_status_service import (
    normalize_simulation_status,
)


def require_simulation_invitable(simulation: Simulation) -> None:
    """Require simulation invitable."""
    current_status = normalize_simulation_status(simulation.status)
    if current_status == SIMULATION_STATUS_TERMINATED:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has been terminated.",
            error_code="SIMULATION_TERMINATED",
            retryable=False,
            details={"status": current_status},
        )
    pending_scenario_version_id = getattr(
        simulation, "pending_scenario_version_id", None
    )
    if pending_scenario_version_id is not None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario approval is pending before inviting.",
            error_code="SCENARIO_APPROVAL_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": pending_scenario_version_id},
        )
    if current_status != SIMULATION_STATUS_ACTIVE_INVITING:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation is not approved for inviting.",
            error_code="SIMULATION_NOT_INVITABLE",
            retryable=False,
            details={"status": current_status},
        )


__all__ = ["require_simulation_invitable"]
