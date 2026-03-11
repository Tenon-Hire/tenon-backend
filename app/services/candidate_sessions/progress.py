from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession, Task
from app.domains.candidate_sessions import repository as cs_repo
from app.domains.candidate_sessions.progress import (
    compute_current_task,
    summarize_progress,
)
from app.services.candidate_sessions.schedule_gates import compute_task_window


async def load_tasks(db: AsyncSession, simulation_id: int) -> list[Task]:
    tasks = await cs_repo.tasks_for_simulation(db, simulation_id)
    if not tasks:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation has no tasks",
        )
    return tasks


async def completed_task_ids(db: AsyncSession, candidate_session_id: int) -> set[int]:
    return await cs_repo.completed_task_ids(db, candidate_session_id)


def _handoff_revisit_task(
    task_list: list[Task],
    completed_ids: set[int],
    current_task: Task | None,
    *,
    candidate_session: CandidateSession,
    now_utc: datetime,
) -> Task | None:
    if current_task is None:
        return None

    current_day = int(current_task.day_index)
    if current_day <= 1:
        return current_task

    prior_day = current_day - 1
    prior_handoff = next(
        (
            task
            for task in task_list
            if int(task.day_index) == prior_day
            and task.id in completed_ids
            and (task.type or "").lower() == "handoff"
        ),
        None,
    )
    if prior_handoff is None:
        return current_task

    next_window = compute_task_window(
        candidate_session,
        current_task,
        now_utc=now_utc,
    )
    if next_window.window_start_at is None:
        return prior_handoff
    if now_utc < next_window.window_start_at:
        return prior_handoff
    return current_task


async def progress_snapshot(
    db: AsyncSession,
    candidate_session: CandidateSession,
    *,
    tasks: list[Task] | None = None,
    now: datetime | None = None,
) -> tuple[list[Task], set[int], Task | None, int, int, bool]:
    task_list = tasks or await load_tasks(db, candidate_session.simulation_id)
    completed_ids = await completed_task_ids(db, candidate_session.id)
    current = compute_current_task(task_list, completed_ids)
    resolved_now = (now or datetime.now(UTC)).astimezone(UTC)
    current = _handoff_revisit_task(
        task_list,
        completed_ids,
        current,
        candidate_session=candidate_session,
        now_utc=resolved_now,
    )
    completed, total, is_complete = summarize_progress(len(task_list), completed_ids)
    return task_list, completed_ids, current, completed, total, is_complete
