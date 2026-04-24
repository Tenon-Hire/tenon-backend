"""Application module for candidates candidate sessions repositories candidates candidate sessions tokens repository workflows."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select

from app.shared.database.shared_database_models_model import CandidateSession
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
    Trial,
)


def _not_terminated_trial_clause():
    return or_(
        Trial.status.is_(None),
        Trial.status != TRIAL_STATUS_TERMINATED,
    )


def _build_get_by_token_stmt(token: str) -> Select:
    return (
        select(CandidateSession)
        .join(CandidateSession.trial)
        .where(
            CandidateSession.token == token,
            _not_terminated_trial_clause(),
        )
        .options(
            joinedload(CandidateSession.trial),
            joinedload(CandidateSession.scenario_version),
        )
    )


def _build_get_by_token_for_update_stmt(token: str) -> Select:
    return _build_get_by_token_stmt(token).with_for_update(of=CandidateSession)


async def get_by_token(db: AsyncSession, token: str) -> CandidateSession | None:
    """Return by token."""
    stmt = _build_get_by_token_stmt(token)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def get_by_token_for_update(
    db: AsyncSession, token: str
) -> CandidateSession | None:
    """Return by token for update."""
    stmt = _build_get_by_token_for_update_stmt(token)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def list_for_email(
    db: AsyncSession, email: str, *, include_terminated: bool = False
) -> list[CandidateSession]:
    """Return for email."""
    stmt = (
        select(CandidateSession)
        .join(Trial, Trial.id == CandidateSession.trial_id)
        .where(func.lower(CandidateSession.invite_email) == func.lower(email))
        .options(
            selectinload(CandidateSession.trial).selectinload(Trial.company),
            selectinload(CandidateSession.winoe_report),
        )
    )
    if not include_terminated:
        stmt = stmt.where(_not_terminated_trial_clause())
    res = await db.execute(stmt)
    return list(res.scalars().unique().all())


__all__ = ["get_by_token", "get_by_token_for_update", "list_for_email"]
