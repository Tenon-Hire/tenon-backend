"""Application module for candidates candidate sessions services candidates candidate sessions progress service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_progress_handoff_service import (
    handoff_revisit_task,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_progress_loaders_service import (
    completed_task_ids as _completed_task_ids,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_progress_loaders_service import (
    load_tasks as _load_tasks,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_progress_loaders_service import (
    load_tasks_with_completion_state,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_gates_service import (
    compute_task_window,
)
from app.candidates.candidate_sessions.utils.candidates_candidate_sessions_utils_candidates_candidate_sessions_progress_utils import (
    compute_current_task,
    summarize_progress,
)
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow


async def load_tasks(db: AsyncSession, trial_id: int) -> list[Task]:
    """Load tasks."""
    return await _load_tasks(
        db,
        trial_id,
        tasks_for_trial=cs_repo.tasks_for_trial,
    )


async def completed_task_ids(db: AsyncSession, candidate_session_id: int) -> set[int]:
    """Execute completed task ids."""
    return await _completed_task_ids(
        db,
        candidate_session_id,
        completed_ids_loader=cs_repo.completed_task_ids,
    )


def _handoff_revisit_task(
    task_list: list[Task],
    completed_ids: set[int],
    current_task: Task | None,
    *,
    candidate_session: CandidateSession,
    now_utc: datetime,
) -> Task | None:
    return handoff_revisit_task(
        task_list,
        completed_ids,
        current_task,
        candidate_session=candidate_session,
        now_utc=now_utc,
        compute_window=compute_task_window,
    )


async def progress_snapshot(
    db: AsyncSession,
    candidate_session: CandidateSession,
    *,
    tasks: list[Task] | None = None,
    now: datetime | None = None,
) -> tuple[list[Task], set[int], Task | None, int, int, bool]:
    """Execute progress snapshot."""
    if tasks:
        task_list = tasks
        completed_ids = await completed_task_ids(db, candidate_session.id)
    else:
        task_list, completed_ids = await load_tasks_with_completion_state(
            db,
            trial_id=candidate_session.trial_id,
            candidate_session_id=candidate_session.id,
        )
    current = compute_current_task(task_list, completed_ids)
    resolved_now = (now or shared_utcnow()).astimezone(UTC)
    current = _handoff_revisit_task(
        task_list,
        completed_ids,
        current,
        candidate_session=candidate_session,
        now_utc=resolved_now,
    )
    completed, total, is_complete = summarize_progress(len(task_list), completed_ids)
    return task_list, completed_ids, current, completed, total, is_complete
