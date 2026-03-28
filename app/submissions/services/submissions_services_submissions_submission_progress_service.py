"""Application module for submissions services submissions submission progress service workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.shared.database.shared_database_models_model import CandidateSession, Task


async def progress_after_submission(
    db: AsyncSession,
    candidate_session: CandidateSession,
    *,
    now: datetime,
    tasks: list[Task] | None = None,
) -> tuple[int, int, bool]:
    """Recompute progress and update completion status if applicable."""
    try:
        snapshot = await cs_service.progress_snapshot(
            db, candidate_session, tasks=tasks
        )
    except TypeError as exc:
        if "tasks" not in str(exc):
            raise
        snapshot = await cs_service.progress_snapshot(db, candidate_session)
    (
        _,
        _completed_task_ids,
        _current,
        completed,
        total,
        is_complete,
    ) = snapshot

    if is_complete and candidate_session.status != "completed":
        candidate_session.status = "completed"
        if candidate_session.completed_at is None:
            candidate_session.completed_at = now
        await db.commit()
        await db.refresh(candidate_session)

    return completed, total, is_complete
