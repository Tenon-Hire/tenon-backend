"""Application module for simulations services simulations candidates compare access service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.evaluations.services.evaluations_services_evaluations_fit_profile_access_service import (
    has_company_access,
)
from app.shared.database.shared_database_models_model import Simulation, User
from app.simulations.services.simulations_services_simulations_candidates_compare_model import (
    SimulationCompareAccessContext,
)


async def require_simulation_compare_access(
    db: AsyncSession,
    *,
    simulation_id: int,
    user: User,
) -> SimulationCompareAccessContext:
    """Require simulation compare access."""
    simulation = (
        await db.execute(
            select(Simulation)
            .options(
                load_only(Simulation.id, Simulation.company_id, Simulation.created_by)
            )
            .where(Simulation.id == simulation_id)
        )
    ).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )
    if not has_company_access(
        simulation_company_id=simulation.company_id,
        expected_company_id=getattr(user, "company_id", None),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation access forbidden",
        )
    if simulation.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation access forbidden",
        )
    return SimulationCompareAccessContext(simulation_id=simulation.id)


__all__ = ["require_simulation_compare_access"]
