"""Application module for simulations services simulations lifecycle access service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Simulation


async def _load_for_lifecycle(
    db: AsyncSession, simulation_id: int, *, for_update: bool
) -> Simulation:
    stmt = select(Simulation).where(Simulation.id == simulation_id)
    if for_update:
        stmt = stmt.with_for_update()
    simulation = (await db.execute(stmt)).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    return simulation


async def require_owner_for_lifecycle(
    db: AsyncSession,
    simulation_id: int,
    actor_user_id: int,
    *,
    for_update: bool = False,
) -> Simulation:
    """Require owner for lifecycle."""
    simulation = await _load_for_lifecycle(db, simulation_id, for_update=for_update)
    if simulation.created_by != actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this simulation",
        )
    return simulation


__all__ = ["require_owner_for_lifecycle"]
