"""Application module for submissions routes submissions helpers routes workflows."""

from contextlib import suppress

from app.submissions.presentation import present_detail, present_list_item
from app.submissions.routes.submissions_routes_submissions_helpers_guard_routes import (
    ensure_recruiter_guard,
)
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    RecruiterSubmissionDetailOut,
    RecruiterSubmissionListItemOut,
    RecruiterSubmissionListOut,
)
from app.submissions.services import service_recruiter as recruiter_sub_service


async def get_submission_detail(
    submission_id: int, db, user
) -> RecruiterSubmissionDetailOut:
    """Return submission detail."""
    ensure_recruiter_guard(user)
    sub, task, cs, sim = await recruiter_sub_service.fetch_detail(
        db, submission_id, user.id
    )
    return RecruiterSubmissionDetailOut(**present_detail(sub, task, cs, sim))


async def list_submissions(
    db,
    user,
    candidateSessionId: int | None = None,
    taskId: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> RecruiterSubmissionListOut:
    """Return submissions."""
    ensure_recruiter_guard(user)
    rows = await recruiter_sub_service.list_submissions(
        db, user.id, candidateSessionId, taskId, limit, offset
    )
    items: list[RecruiterSubmissionListItemOut] = []
    for row in rows:
        sub = row
        task = None
        with suppress(TypeError, ValueError):
            sub, task, *_ = row
        if task is None:
            continue
        items.append(RecruiterSubmissionListItemOut(**present_list_item(sub, task)))
    return RecruiterSubmissionListOut(items=items)


__all__ = ["get_submission_detail", "list_submissions"]
