"""Application module for simulations services simulations lifecycle service workflows."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import ScenarioVersion, Simulation, Task
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
from app.simulations.services.simulations_services_simulations_codespace_specializer_service import (
    ensure_precommit_bundle_prepared_for_approved_scenario,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_create_service import (
    get_active_scenario_version,
)

logger = logging.getLogger(__name__)


async def _load_simulation_tasks(db: AsyncSession, simulation_id: int) -> list[Task]:
    return (
        (
            await db.execute(
                select(Task)
                .where(Task.simulation_id == simulation_id)
                .order_by(Task.day_index.asc())
            )
        )
        .scalars()
        .all()
    )


async def _prepare_active_scenario_bundle_on_activation(
    db: AsyncSession,
    *,
    simulation: Simulation,
) -> ScenarioVersion | None:
    active_scenario_version = await get_active_scenario_version(db, simulation.id)
    if active_scenario_version is None:
        return None
    tasks = await _load_simulation_tasks(db, simulation.id)
    await ensure_precommit_bundle_prepared_for_approved_scenario(
        db,
        simulation=simulation,
        scenario_version=active_scenario_version,
        tasks=tasks,
    )
    await db.commit()
    return active_scenario_version


async def activate_simulation(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    now: datetime | None = None,
) -> Simulation:
    """Activate simulation."""
    simulation = await _transition_owned_simulation_impl(
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
    await _prepare_active_scenario_bundle_on_activation(db, simulation=simulation)
    await db.refresh(simulation)
    return simulation


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
