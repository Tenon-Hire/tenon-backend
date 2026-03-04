from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession
from app.domains.candidate_sessions import repository as cs_repo
from app.domains.candidate_sessions.service.status import require_not_expired
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED


def _loaded_simulation_status(cs: CandidateSession) -> str | None:
    try:
        state = inspect(cs)
    except NoInspectionAvailable:
        simulation = getattr(cs, "simulation", None)
        return getattr(simulation, "status", None)

    if "simulation" in state.unloaded:
        return None

    simulation = state.attrs.simulation.value
    return getattr(simulation, "status", None)


def _ensure_simulation_not_terminated(cs: CandidateSession) -> None:
    if _loaded_simulation_status(cs) == SIMULATION_STATUS_TERMINATED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite token",
        )


async def fetch_by_token(db: AsyncSession, token: str, *, now=None) -> CandidateSession:
    cs = await cs_repo.get_by_token(db, token)
    if cs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite token"
        )
    _ensure_simulation_not_terminated(cs)
    require_not_expired(cs, now=now)
    return cs


async def fetch_by_token_for_update(
    db: AsyncSession, token: str, *, now=None
) -> CandidateSession:
    cs = await cs_repo.get_by_token_for_update(db, token)
    if cs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite token"
        )
    _ensure_simulation_not_terminated(cs)
    require_not_expired(cs, now=now)
    return cs


__all__ = ["fetch_by_token", "fetch_by_token_for_update"]
