"""Application module for evaluations services evaluations fit profile pipeline queries service workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.shared.database.shared_database_models_model import (
    CandidateDayAudit,
    Submission,
    Task,
)


async def _submissions_by_day(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    simulation_id: int,
) -> dict[int, Submission]:
    rows = (
        await db.execute(
            select(Submission, Task)
            .join(Task, Task.id == Submission.task_id)
            .where(
                Submission.candidate_session_id == candidate_session_id,
                Task.simulation_id == simulation_id,
            )
            .order_by(Task.day_index.asc())
        )
    ).all()
    by_day: dict[int, Submission] = {}
    for submission, task in rows:
        by_day[task.day_index] = submission
    return by_day


async def _tasks_by_day(db: AsyncSession, *, simulation_id: int) -> dict[int, Task]:
    tasks = (
        (
            await db.execute(
                select(Task)
                .where(Task.simulation_id == simulation_id)
                .order_by(Task.day_index.asc(), Task.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return {task.day_index: task for task in tasks}


async def _day_audits_by_day(
    db: AsyncSession,
    *,
    candidate_session_id: int,
) -> dict[int, CandidateDayAudit]:
    rows = await cs_repo.list_day_audits(
        db,
        candidate_session_ids=[candidate_session_id],
        day_indexes=[2, 3],
    )
    return {row.day_index: row for row in rows}


__all__ = ["_day_audits_by_day", "_submissions_by_day", "_tasks_by_day"]
