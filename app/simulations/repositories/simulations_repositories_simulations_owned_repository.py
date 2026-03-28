"""Application module for simulations repositories simulations owned repository workflows."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Simulation, Task
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_TERMINATED,
)


async def get_owned(
    db: AsyncSession,
    simulation_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> Simulation | None:
    """Fetch a simulation only if owned by given user."""
    stmt = select(Simulation).where(
        Simulation.id == simulation_id,
        Simulation.created_by == user_id,
    )
    if not include_terminated:
        stmt = stmt.where(
            or_(
                Simulation.status.is_(None),
                Simulation.status != SIMULATION_STATUS_TERMINATED,
            )
        )
    if for_update:
        stmt = stmt.with_for_update(of=Simulation)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_owned_with_tasks(
    db: AsyncSession,
    simulation_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> tuple[Simulation | None, list[Task]]:
    """Fetch a simulation with tasks if owned by given user."""
    stmt = (
        select(Simulation, Task)
        .outerjoin(Task, Task.simulation_id == Simulation.id)
        .where(
            Simulation.id == simulation_id,
            Simulation.created_by == user_id,
        )
        .order_by(Task.day_index.asc(), Task.id.asc())
    )
    if not include_terminated:
        stmt = stmt.where(
            or_(
                Simulation.status.is_(None),
                Simulation.status != SIMULATION_STATUS_TERMINATED,
            )
        )
    if for_update:
        stmt = stmt.with_for_update(of=Simulation)

    rows = (await db.execute(stmt)).all()
    if not rows:
        return None, []

    sim = rows[0][0]
    tasks = [task for _, task in rows if task is not None]
    return sim, tasks
