"""Application module for jobs handlers day close finalize text queries handler workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Submission,
    Task,
)


async def _load_candidate_session(db, *, candidate_session_id: int):
    return (
        await db.execute(
            select(CandidateSession)
            .where(CandidateSession.id == candidate_session_id)
            .options(selectinload(CandidateSession.trial))
        )
    ).scalar_one_or_none()


async def _load_task_for_session(db, *, task_id: int, trial_id: int):
    return (
        await db.execute(
            select(Task).where(Task.id == task_id, Task.trial_id == trial_id)
        )
    ).scalar_one_or_none()


async def _get_existing_submission(
    db, *, candidate_session_id: int, task_id: int
) -> Submission | None:
    return (
        await db.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session_id,
                Submission.task_id == task_id,
            )
        )
    ).scalar_one_or_none()


__all__ = [
    "_get_existing_submission",
    "_load_candidate_session",
    "_load_task_for_session",
]
