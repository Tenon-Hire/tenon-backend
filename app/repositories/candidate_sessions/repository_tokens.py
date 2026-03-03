from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains import CandidateSession
from app.domains.simulations.simulation import Simulation
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED


async def get_by_token(
    db: AsyncSession, token: str, *, with_simulation: bool = False
) -> CandidateSession | None:
    stmt = select(CandidateSession).where(CandidateSession.token == token)
    if with_simulation:
        stmt = stmt.options(selectinload(CandidateSession.simulation))
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def get_by_token_for_update(
    db: AsyncSession, token: str
) -> CandidateSession | None:
    stmt = (
        select(CandidateSession)
        .where(CandidateSession.token == token)
        .options(selectinload(CandidateSession.simulation))
        .with_for_update()
    )
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
        stmt = stmt.where(
            or_(
                Simulation.status.is_(None),
                Simulation.status != SIMULATION_STATUS_TERMINATED,
            )
        )
    res = await db.execute(stmt)
    return list(res.scalars().unique().all())


__all__ = ["get_by_token", "get_by_token_for_update", "list_for_email"]
