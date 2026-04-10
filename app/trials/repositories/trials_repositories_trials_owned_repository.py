"""Application module for trials repositories trials owned repository workflows."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Task, Trial
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)


async def get_owned(
    db: AsyncSession,
    trial_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> Trial | None:
    """Fetch a trial only if owned by given user."""
    stmt = select(Trial).where(
        Trial.id == trial_id,
        Trial.created_by == user_id,
    )
    if not include_terminated:
        stmt = stmt.where(
            or_(
                Trial.status.is_(None),
                Trial.status != TRIAL_STATUS_TERMINATED,
            )
        )
    if for_update:
        stmt = stmt.with_for_update(of=Trial)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_owned_with_tasks(
    db: AsyncSession,
    trial_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> tuple[Trial | None, list[Task]]:
    """Fetch a trial with tasks if owned by given user."""
    stmt = (
        select(Trial, Task)
        .outerjoin(Task, Task.trial_id == Trial.id)
        .where(
            Trial.id == trial_id,
            Trial.created_by == user_id,
        )
        .order_by(Task.day_index.asc(), Task.id.asc())
    )
    if not include_terminated:
        stmt = stmt.where(
            or_(
                Trial.status.is_(None),
                Trial.status != TRIAL_STATUS_TERMINATED,
            )
        )
    if for_update:
        stmt = stmt.with_for_update(of=Trial)

    rows = (await db.execute(stmt)).all()
    if not rows:
        return None, []

    sim = rows[0][0]
    tasks = [task for _, task in rows if task is not None]
    return sim, tasks
