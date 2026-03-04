from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.domains import CandidateSession
from app.domains.simulations.simulation import Simulation
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED


def _not_terminated_simulation_clause():
    return or_(
        Simulation.status.is_(None),
        Simulation.status != SIMULATION_STATUS_TERMINATED,
    )


def _build_get_by_token_stmt(token: str) -> Select:
    return (
        select(CandidateSession)
        .join(Simulation, Simulation.id == CandidateSession.simulation_id)
        .where(
            CandidateSession.token == token,
            _not_terminated_simulation_clause(),
        )
        .options(selectinload(CandidateSession.simulation))
    )


def _build_get_by_token_for_update_stmt(token: str) -> Select:
    return _build_get_by_token_stmt(token).with_for_update(of=CandidateSession)


async def get_by_token(db: AsyncSession, token: str) -> CandidateSession | None:
    stmt = _build_get_by_token_stmt(token)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def get_by_token_for_update(
    db: AsyncSession, token: str
) -> CandidateSession | None:
    stmt = _build_get_by_token_for_update_stmt(token)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def list_for_email(
    db: AsyncSession, email: str, *, include_terminated: bool = False
) -> list[CandidateSession]:
    stmt = (
        select(CandidateSession)
        .join(Simulation, Simulation.id == CandidateSession.simulation_id)
        .where(func.lower(CandidateSession.invite_email) == func.lower(email))
        .options(
            selectinload(CandidateSession.simulation).selectinload(Simulation.company)
        )
    )
    if not include_terminated:
        stmt = stmt.where(_not_terminated_simulation_clause())
    res = await db.execute(stmt)
    return list(res.scalars().unique().all())


__all__ = ["get_by_token", "get_by_token_for_update", "list_for_email"]
