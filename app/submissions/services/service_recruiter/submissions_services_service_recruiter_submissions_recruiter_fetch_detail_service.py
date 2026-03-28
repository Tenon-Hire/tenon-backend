"""Application module for submissions services service recruiter submissions recruiter fetch detail service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Simulation,
    Submission,
    Task,
)


async def fetch_detail(
    db: AsyncSession,
    submission_id: int,
    recruiter_id: int,
    recruiter_company_id: int | None = None,
) -> tuple[Submission, Task, CandidateSession, Simulation]:
    """Load submission with task/session/simulation; enforce recruiter access."""
    stmt = (
        select(Submission, Task, CandidateSession, Simulation)
        .join(Task, Task.id == Submission.task_id)
        .join(CandidateSession, CandidateSession.id == Submission.candidate_session_id)
        .join(Simulation, Simulation.id == CandidateSession.simulation_id)
        .where(Submission.id == submission_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    _sub, _task, _cs, simulation = row
    if recruiter_company_id is not None:
        if simulation.company_id != recruiter_company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submission access forbidden",
            )
    elif simulation.created_by != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    return row
