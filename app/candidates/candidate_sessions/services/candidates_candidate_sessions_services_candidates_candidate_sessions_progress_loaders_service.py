"""Application module for candidates candidate sessions services candidates candidate sessions progress loaders service workflows."""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.shared.database.shared_database_models_model import Submission, Task


def _raise_missing_tasks() -> None:
    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Simulation has no tasks",
    )


async def load_tasks(
    db: AsyncSession,
    simulation_id: int,
    *,
    tasks_for_simulation=None,
) -> list[Task]:
    """Load tasks."""
    loader = tasks_for_simulation or cs_repo.tasks_for_simulation
    tasks = await loader(db, simulation_id)
    if not tasks:
        _raise_missing_tasks()
    return tasks


async def completed_task_ids(
    db: AsyncSession,
    candidate_session_id: int,
    *,
    completed_ids_loader=None,
) -> set[int]:
    """Execute completed task ids."""
    loader = completed_ids_loader or cs_repo.completed_task_ids
    return await loader(db, candidate_session_id)


async def load_tasks_with_completion_state(
    db: AsyncSession,
    *,
    simulation_id: int,
    candidate_session_id: int,
) -> tuple[list[Task], set[int]]:
    """Load tasks with completion state."""
    stmt = (
        select(Task, Submission.id)
        .outerjoin(
            Submission,
            and_(
                Submission.task_id == Task.id,
                Submission.candidate_session_id == candidate_session_id,
            ),
        )
        .where(Task.simulation_id == simulation_id)
        .order_by(Task.day_index.asc(), Task.id.asc())
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        _raise_missing_tasks()

    task_by_id: dict[int, Task] = {}
    completed_ids: set[int] = set()
    for task, submission_id in rows:
        task_by_id.setdefault(task.id, task)
        if submission_id is not None:
            completed_ids.add(task.id)
    return list(task_by_id.values()), completed_ids
