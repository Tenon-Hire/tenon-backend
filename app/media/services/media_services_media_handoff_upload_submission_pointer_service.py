"""Application module for media services media handoff upload submission pointer service workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories import repository as submissions_repo


async def upsert_submission_recording_pointer(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    recording_id: int,
    submitted_at: datetime,
) -> int:
    """Upsert submission recording pointer."""
    return await submissions_repo.upsert_handoff_submission(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        recording_id=recording_id,
        submitted_at=submitted_at,
    )


__all__ = ["upsert_submission_recording_pointer"]
