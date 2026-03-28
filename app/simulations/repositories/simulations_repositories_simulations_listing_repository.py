"""Application module for simulations repositories simulations listing repository workflows."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Simulation,
)
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_TERMINATED,
)


async def list_with_candidate_counts(
    db: AsyncSession, user_id: int, *, include_terminated: bool = False
):
    """List simulations owned by user with candidate counts."""
    counts_subq = (
        select(
            CandidateSession.simulation_id.label("simulation_id"),
            func.count(CandidateSession.id).label("num_candidates"),
        )
        .group_by(CandidateSession.simulation_id)
        .subquery()
    )

    stmt = (
        select(
            Simulation,
            func.coalesce(counts_subq.c.num_candidates, 0).label("num_candidates"),
        )
        .outerjoin(counts_subq, counts_subq.c.simulation_id == Simulation.id)
        .where(Simulation.created_by == user_id)
        .order_by(Simulation.created_at.desc())
    )
    if not include_terminated:
        stmt = stmt.where(
            or_(
                Simulation.status.is_(None),
                Simulation.status != SIMULATION_STATUS_TERMINATED,
            )
        )

    result = await db.execute(stmt)
    return result.all()
