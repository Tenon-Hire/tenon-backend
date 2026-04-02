"""Application module for candidates candidate sessions repositories candidates candidate sessions basic repository workflows."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.sql import Select

from app.shared.database.shared_database_models_model import CandidateSession
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_TERMINATED,
    Simulation,
)


def _not_terminated_simulation_clause():
    return or_(
        Simulation.status.is_(None),
        Simulation.status != SIMULATION_STATUS_TERMINATED,
    )


def _build_get_by_id_stmt(session_id: int) -> Select:
    return (
        select(CandidateSession)
        .join(Simulation, Simulation.id == CandidateSession.simulation_id)
        .where(
            CandidateSession.id == session_id,
            _not_terminated_simulation_clause(),
        )
        .options(
            contains_eager(CandidateSession.simulation),
            joinedload(CandidateSession.scenario_version),
        )
    )


def _build_get_by_id_for_update_stmt(session_id: int) -> Select:
    return _build_get_by_id_stmt(session_id).with_for_update(of=CandidateSession)


async def get_by_id(db: AsyncSession, session_id: int) -> CandidateSession | None:
    """Return by id."""
    res = await db.execute(_build_get_by_id_stmt(session_id))
    return res.scalar_one_or_none()


async def get_by_id_for_update(
    db: AsyncSession, session_id: int
) -> CandidateSession | None:
    """Return by id for update."""
    res = await db.execute(_build_get_by_id_for_update_stmt(session_id))
    return res.scalar_one_or_none()


__all__ = ["get_by_id", "get_by_id_for_update"]
