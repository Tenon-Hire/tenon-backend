"""Application module for simulations services simulations ownership service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Simulation, Task


async def require_owned_simulation(
    db: AsyncSession,
    simulation_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> Simulation:
    """Require owned simulation."""
    from app.simulations import services as sim_service

    sim = await sim_service.sim_repo.get_owned(
        db,
        simulation_id,
        user_id,
        include_terminated=include_terminated,
        for_update=for_update,
    )
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    return sim


async def require_owned_simulation_with_tasks(
    db: AsyncSession,
    simulation_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> tuple[Simulation, list[Task]]:
    """Require owned simulation with tasks."""
    from app.simulations import services as sim_service

    sim, tasks = await sim_service.sim_repo.get_owned_with_tasks(
        db,
        simulation_id,
        user_id,
        include_terminated=include_terminated,
        for_update=for_update,
    )
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    return sim, tasks
