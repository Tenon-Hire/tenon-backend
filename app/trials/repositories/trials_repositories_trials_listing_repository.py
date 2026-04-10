"""Application module for trials repositories trials listing repository workflows."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)


async def list_with_candidate_counts(
    db: AsyncSession, user_id: int, *, include_terminated: bool = False
):
    """List trials owned by user with candidate counts."""
    counts_subq = (
        select(
            CandidateSession.trial_id.label("trial_id"),
            func.count(CandidateSession.id).label("num_candidates"),
        )
        .group_by(CandidateSession.trial_id)
        .subquery()
    )

    stmt = (
        select(
            Trial,
            func.coalesce(counts_subq.c.num_candidates, 0).label("num_candidates"),
        )
        .outerjoin(counts_subq, counts_subq.c.trial_id == Trial.id)
        .where(Trial.created_by == user_id)
        .order_by(Trial.created_at.desc())
    )
    if not include_terminated:
        stmt = stmt.where(
            or_(
                Trial.status.is_(None),
                Trial.status != TRIAL_STATUS_TERMINATED,
            )
        )

    result = await db.execute(stmt)
    return result.all()
