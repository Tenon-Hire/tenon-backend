"""Application module for media services media handoff upload lookup service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Simulation,
    Task,
)


async def load_task_with_company_or_404(
    db: AsyncSession, task_id: int
) -> tuple[Task, int]:
    """Load task with company or 404."""
    row = (
        await db.execute(
            select(Task, Simulation.company_id)
            .join(Simulation, Simulation.id == Task.simulation_id)
            .where(Task.id == task_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    task, company_id = row
    if not isinstance(company_id, int):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation metadata unavailable",
        )
    return task, company_id


async def resolve_company_id(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    simulation_id: int,
) -> int:
    """Resolve company id."""
    simulation = candidate_session.__dict__.get("simulation")
    if simulation is not None and isinstance(
        getattr(simulation, "company_id", None), int
    ):
        return simulation.company_id
    company_id = (
        await db.execute(
            select(Simulation.company_id).where(Simulation.id == simulation_id)
        )
    ).scalar_one_or_none()
    if not isinstance(company_id, int):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation metadata unavailable",
        )
    return company_id


__all__ = ["load_task_with_company_or_404", "resolve_company_id"]
