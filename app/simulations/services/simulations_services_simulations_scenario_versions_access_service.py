"""Application module for simulations services simulations scenario versions access service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import ScenarioVersion, Simulation
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.scenario_versions import (
    simulations_repositories_scenario_versions_simulations_scenario_versions_repository as scenario_repo,
)


async def require_owned_simulation_for_update(
    db: AsyncSession, simulation_id: int, actor_user_id: int
) -> Simulation:
    """Require owned simulation for update."""
    stmt = select(Simulation).where(Simulation.id == simulation_id).with_for_update()
    simulation = (await db.execute(stmt)).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    if simulation.created_by != actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this simulation",
        )
    return simulation


def scenario_generation_idempotency_key(scenario_version_id: int) -> str:
    """Execute scenario generation idempotency key."""
    return f"scenario_version:{scenario_version_id}:scenario_generation"


def raise_active_scenario_missing() -> None:
    """Execute raise active scenario missing."""
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Simulation has no active scenario version.",
        error_code="SCENARIO_ACTIVE_VERSION_MISSING",
        retryable=False,
        details={},
    )


async def get_active_scenario_for_update(
    db: AsyncSession, simulation: Simulation
) -> ScenarioVersion:
    """Return active scenario for update."""
    active_scenario_version_id = simulation.active_scenario_version_id
    if active_scenario_version_id is None:
        raise_active_scenario_missing()
    active = await scenario_repo.get_by_id(
        db, active_scenario_version_id, for_update=True
    )
    if active is None or active.simulation_id != simulation.id:
        raise_active_scenario_missing()
    return active
