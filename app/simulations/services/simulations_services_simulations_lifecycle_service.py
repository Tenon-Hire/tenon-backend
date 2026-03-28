"""Application module for simulations services simulations lifecycle service workflows."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Simulation
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_ACTIVE_INVITING,
)
from app.simulations.services.simulations_services_simulations_lifecycle_access_service import (
    require_owner_for_lifecycle,
)
from app.simulations.services.simulations_services_simulations_lifecycle_actions_service import (
    _transition_owned_simulation_impl,
)
from app.simulations.services.simulations_services_simulations_lifecycle_invitable_service import (
    require_simulation_invitable,
)
from app.simulations.services.simulations_services_simulations_lifecycle_status_service import (
    normalize_simulation_status,
    normalize_simulation_status_or_raise,
)
from app.simulations.services.simulations_services_simulations_lifecycle_termination_service import (
    TerminateSimulationResult,
    terminate_simulation_with_cleanup_impl,
)
from app.simulations.services.simulations_services_simulations_lifecycle_transition_rules_service import (
    apply_status_transition,
)

logger = logging.getLogger(__name__)


async def activate_simulation(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    now: datetime | None = None,
) -> Simulation:
    """Activate simulation."""
    return await _transition_owned_simulation_impl(
        db,
        simulation_id=simulation_id,
        actor_user_id=actor_user_id,
        target_status=SIMULATION_STATUS_ACTIVE_INVITING,
        now=now,
        require_owner=require_owner_for_lifecycle,
        apply_transition=apply_status_transition,
        normalize_status=normalize_simulation_status,
        logger=logger,
    )


async def terminate_simulation(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
) -> Simulation:
    """Terminate simulation."""
    return (
        await terminate_simulation_with_cleanup(
            db,
            simulation_id=simulation_id,
            actor_user_id=actor_user_id,
            reason=reason,
            now=now,
        )
    ).simulation


async def terminate_simulation_with_cleanup(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
) -> TerminateSimulationResult:
    """Terminate simulation with cleanup."""
    return await terminate_simulation_with_cleanup_impl(
        db,
        simulation_id=simulation_id,
        actor_user_id=actor_user_id,
        reason=reason,
        now=now,
        require_owner=require_owner_for_lifecycle,
        apply_transition=apply_status_transition,
        normalize_status=normalize_simulation_status,
        logger=logger,
    )


__all__ = [
    "TerminateSimulationResult",
    "activate_simulation",
    "apply_status_transition",
    "normalize_simulation_status",
    "normalize_simulation_status_or_raise",
    "require_owner_for_lifecycle",
    "require_simulation_invitable",
    "terminate_simulation",
    "terminate_simulation_with_cleanup",
]
