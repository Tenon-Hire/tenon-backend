"""Application module for candidates candidate sessions repositories candidates candidate sessions submissions repository workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Submission


async def last_submission_at(
    db: AsyncSession, candidate_session_id: int
) -> datetime | None:
    """Execute last submission at."""
    stmt = select(func.max(Submission.submitted_at)).where(
        Submission.candidate_session_id == candidate_session_id
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def last_submission_at_bulk(
    db: AsyncSession, candidate_session_ids: list[int]
) -> dict[int, datetime | None]:
    """Execute last submission at bulk."""
    if not candidate_session_ids:
        return {}
    stmt = (
        select(
            Submission.candidate_session_id,
            func.max(Submission.submitted_at),
        )
        .where(Submission.candidate_session_id.in_(candidate_session_ids))
        .group_by(Submission.candidate_session_id)
    )
    res = await db.execute(stmt)
    return {row[0]: row[1] for row in res.all()}


__all__ = ["last_submission_at", "last_submission_at_bulk"]
