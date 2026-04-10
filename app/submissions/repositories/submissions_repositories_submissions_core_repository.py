"""Application module for submissions repositories submissions core repository workflows."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from .submissions_repositories_submissions_handoff_upsert_repository import (
    upsert_handoff_submission as _upsert_handoff_submission,
)
from .submissions_repositories_submissions_handoff_write_repository import (
    create_handoff_submission,
    update_handoff_submission,
)
from .submissions_repositories_submissions_lookup_repository import (
    find_duplicate,
    get_by_candidate_session_task,
    trial_template,
)


async def upsert_handoff_submission(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    recording_id: int,
    submitted_at: datetime,
) -> int:
    """Upsert handoff submission."""
    return await _upsert_handoff_submission(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        recording_id=recording_id,
        submitted_at=submitted_at,
        get_by_candidate_session_task_fn=get_by_candidate_session_task,
        create_handoff_submission_fn=create_handoff_submission,
    )


__all__ = [
    "create_handoff_submission",
    "find_duplicate",
    "get_by_candidate_session_task",
    "trial_template",
    "update_handoff_submission",
    "upsert_handoff_submission",
]
