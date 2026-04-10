"""Application module for media services media handoff upload lookup service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Task,
    Trial,
)


async def load_task_with_company_or_404(
    db: AsyncSession, task_id: int
) -> tuple[Task, int]:
    """Load task with company or 404."""
    row = (
        await db.execute(
            select(Task, Trial.company_id)
            .join(Trial, Trial.id == Task.trial_id)
            .where(Task.id == task_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    task, company_id = row
    if not isinstance(company_id, int):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Trial metadata unavailable",
        )
    return task, company_id


async def resolve_company_id(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    trial_id: int,
) -> int:
    """Resolve company id."""
    trial = candidate_session.__dict__.get("trial")
    if trial is not None and isinstance(getattr(trial, "company_id", None), int):
        return trial.company_id
    company_id = (
        await db.execute(select(Trial.company_id).where(Trial.id == trial_id))
    ).scalar_one_or_none()
    if not isinstance(company_id, int):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Trial metadata unavailable",
        )
    return company_id


__all__ = ["load_task_with_company_or_404", "resolve_company_id"]
