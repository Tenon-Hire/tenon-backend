"""Application module for candidates candidate sessions repositories candidates candidate sessions tasks repository workflows."""

from __future__ import annotations

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Submission, Task


async def tasks_for_simulation(db: AsyncSession, simulation_id: int) -> list[Task]:
    """Execute tasks for simulation."""
    tasks_stmt = (
        select(Task)
        .where(Task.simulation_id == simulation_id)
        .order_by(Task.day_index.asc())
    )
    tasks_res = await db.execute(tasks_stmt)
    return list(tasks_res.scalars().all())


async def completed_task_ids(db: AsyncSession, candidate_session_id: int) -> set[int]:
    """Execute completed task ids."""
    completed_stmt = select(distinct(Submission.task_id)).where(
        Submission.candidate_session_id == candidate_session_id
    )
    completed_res = await db.execute(completed_stmt)
    return set(completed_res.scalars().all())


async def completed_task_ids_bulk(
    db: AsyncSession, candidate_session_ids: list[int]
) -> dict[int, set[int]]:
    """Execute completed task ids bulk."""
    if not candidate_session_ids:
        return {}

    stmt = (
        select(Submission.candidate_session_id, Submission.task_id)
        .where(Submission.candidate_session_id.in_(candidate_session_ids))
        .distinct()
    )
    rows = (await db.execute(stmt)).all()
    result: dict[int, set[int]] = {
        int(session_id): set() for session_id in candidate_session_ids
    }
    for candidate_session_id, task_id in rows:
        if candidate_session_id is None or task_id is None:
            continue
        result.setdefault(int(candidate_session_id), set()).add(int(task_id))
    return result


__all__ = ["tasks_for_simulation", "completed_task_ids", "completed_task_ids_bulk"]
