"""Application module for simulations repositories scenario versions simulations scenario versions repository workflows."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    ScenarioVersion,
)
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    Simulation,
)


async def get_by_id(
    db: AsyncSession, scenario_version_id: int, *, for_update: bool = False
) -> ScenarioVersion | None:
    """Return by id."""
    stmt = select(ScenarioVersion).where(ScenarioVersion.id == scenario_version_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_active_for_simulation(
    db: AsyncSession,
    simulation_id: int,
    *,
    for_update: bool = False,
) -> ScenarioVersion | None:
    """Return active for simulation."""
    stmt = select(ScenarioVersion).join(
        Simulation,
        Simulation.active_scenario_version_id == ScenarioVersion.id,
    )
    stmt = stmt.where(Simulation.id == simulation_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def next_version_index(db: AsyncSession, simulation_id: int) -> int:
    """Execute next version index."""
    max_idx = (
        await db.execute(
            select(func.max(ScenarioVersion.version_index)).where(
                ScenarioVersion.simulation_id == simulation_id
            )
        )
    ).scalar_one_or_none()
    return int(max_idx or 0) + 1


__all__ = ["get_by_id", "get_active_for_simulation", "next_version_index"]
