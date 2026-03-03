from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Simulation, Task
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED


async def get_owned(
    db: AsyncSession,
    simulation_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
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
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_owned_with_tasks(
    db: AsyncSession,
    simulation_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
) -> tuple[Simulation | None, list[Task]]:
    """Fetch a simulation with tasks if owned by given user."""
    sim = await get_owned(
        db,
        simulation_id,
        user_id,
        include_terminated=include_terminated,
    )
    if sim is None:
        return None, []

    tasks_stmt = (
        select(Task).where(Task.simulation_id == sim.id).order_by(Task.day_index.asc())
    )
    tasks = (await db.execute(tasks_stmt)).scalars().all()
    return sim, tasks
