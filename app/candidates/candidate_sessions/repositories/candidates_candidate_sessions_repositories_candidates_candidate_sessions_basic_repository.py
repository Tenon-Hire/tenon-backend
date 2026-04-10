"""Application module for candidates candidate sessions repositories candidates candidate sessions basic repository workflows."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload
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


def _build_get_by_id_stmt(session_id: int) -> Select:
    return (
        select(CandidateSession)
        .join(Trial, Trial.id == CandidateSession.trial_id)
        .where(
            CandidateSession.id == session_id,
            _not_terminated_trial_clause(),
        )
        .options(
            contains_eager(CandidateSession.trial),
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
