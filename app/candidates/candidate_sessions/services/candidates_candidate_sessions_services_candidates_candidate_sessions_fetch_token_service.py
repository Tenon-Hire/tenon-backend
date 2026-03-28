"""Application module for candidates candidate sessions services candidates candidate sessions fetch token service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_status_service import (
    require_not_expired,
)
from app.shared.database.shared_database_models_model import CandidateSession
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_TERMINATED,
)

_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Invalid invite token",
)


def _loaded_simulation_status(cs: CandidateSession) -> str | None:
    try:
        state = inspect(cs)
    except NoInspectionAvailable:
        simulation = getattr(cs, "simulation", None)
        return getattr(simulation, "status", None)

    if "simulation" in state.unloaded:
        raise _INVALID_TOKEN

    simulation = state.attrs.simulation.value
    if simulation is None:
        raise _INVALID_TOKEN
    return getattr(simulation, "status", None)


def _ensure_simulation_not_terminated(cs: CandidateSession) -> None:
    if _loaded_simulation_status(cs) == SIMULATION_STATUS_TERMINATED:
        raise _INVALID_TOKEN


async def fetch_by_token(db: AsyncSession, token: str, *, now=None) -> CandidateSession:
    """Return by token."""
    cs = await cs_repo.get_by_token(db, token)
    if cs is None:
        raise _INVALID_TOKEN
    _ensure_simulation_not_terminated(cs)
    require_not_expired(cs, now=now)
    return cs


async def fetch_by_token_for_update(
    db: AsyncSession, token: str, *, now=None
) -> CandidateSession:
    """Return by token for update."""
    cs = await cs_repo.get_by_token_for_update(db, token)
    if cs is None:
        raise _INVALID_TOKEN
    _ensure_simulation_not_terminated(cs)
    require_not_expired(cs, now=now)
    return cs


__all__ = ["fetch_by_token", "fetch_by_token_for_update"]
