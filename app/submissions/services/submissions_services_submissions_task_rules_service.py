"""Application module for submissions services submissions task rules service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    SubmissionConflict,
    SubmissionOrderError,
    TrialComplete,
)


def ensure_task_belongs(task: Task, candidate_session: CandidateSession) -> None:
    """Ensure the task is part of the candidate's trial."""
    if task.trial_id != candidate_session.trial_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )


async def ensure_not_duplicate(
    db: AsyncSession, candidate_session_id: int, task_id: int
) -> None:
    """Guard against duplicate submissions for a task."""
    from app.submissions.services import (
        submissions_services_submissions_candidate_service as svc,
    )

    if await svc.submissions_repo.find_duplicate(db, candidate_session_id, task_id):
        raise SubmissionConflict()


def ensure_in_order(current_task: Task | None, target_task_id: int) -> None:
    """Verify the submission is for the current task in sequence."""
    if current_task is None:
        raise TrialComplete()
    if current_task.id != target_task_id:
        raise SubmissionOrderError()
