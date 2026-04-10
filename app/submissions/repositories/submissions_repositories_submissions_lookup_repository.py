"""Application module for submissions repositories submissions lookup repository workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Submission, Trial


async def find_duplicate(
    db: AsyncSession, candidate_session_id: int, task_id: int
) -> bool:
    """Return duplicate."""
    dup_stmt = select(Submission.id).where(
        Submission.candidate_session_id == candidate_session_id,
        Submission.task_id == task_id,
    )
    dup_res = await db.execute(dup_stmt)
    return dup_res.scalar_one_or_none() is not None


async def trial_template(db: AsyncSession, trial_id: int) -> str | None:
    """Execute trial template."""
    stmt = select(Trial.scenario_template, Trial.focus).where(Trial.id == trial_id)
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        return None
    scenario_template, focus = row
    return scenario_template or focus


async def get_by_candidate_session_task(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    for_update: bool = False,
) -> Submission | None:
    """Return by candidate session task."""
    stmt = select(Submission).where(
        Submission.candidate_session_id == candidate_session_id,
        Submission.task_id == task_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
