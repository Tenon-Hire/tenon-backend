"""Application module for submissions services service Talent Partner submissions Talent Partner fetch detail service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Submission,
    Task,
    Trial,
)


async def fetch_detail(
    db: AsyncSession,
    submission_id: int,
    talent_partner_id: int,
    talent_partner_company_id: int | None = None,
) -> tuple[Submission, Task, CandidateSession, Trial]:
    """Load submission with task/session/trial; enforce Talent Partner access."""
    stmt = (
        select(Submission, Task, CandidateSession, Trial)
        .join(Task, Task.id == Submission.task_id)
        .join(CandidateSession, CandidateSession.id == Submission.candidate_session_id)
        .join(Trial, Trial.id == CandidateSession.trial_id)
        .where(Submission.id == submission_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    _sub, _task, _cs, trial = row
    if talent_partner_company_id is not None:
        if trial.company_id != talent_partner_company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submission access forbidden",
            )
    elif trial.created_by != talent_partner_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    return row
