"""Aggregated recruiter submissions router."""

from contextlib import suppress

from fastapi import APIRouter

from app.api.routes.submissions_routes import list
from app.api.routes.submissions_routes import router as submissions_router
from app.domains.submissions import service_recruiter as recruiter_sub_service
from app.domains.submissions.presenter import build_diff_url as _build_diff_url
from app.domains.submissions.presenter import (
    build_test_results as _build_test_results,
)
from app.domains.submissions.presenter import (
    parse_diff_summary as _parse_diff_summary,
)
from app.domains.submissions.presenter import (
    present_detail,
    present_list_item,
)
from app.domains.submissions.presenter import (
    redact_text as _redact_text,
)
from app.domains.submissions.presenter import (
    truncate_output as _truncate_output,
)
from app.domains.submissions.schemas import (
    RecruiterSubmissionDetailOut,
    RecruiterSubmissionListItemOut,
    RecruiterSubmissionListOut,
)
from app.infra.security.roles import ensure_recruiter

router = APIRouter()
router.include_router(submissions_router)
_derive_test_status = recruiter_sub_service.derive_test_status


async def get_submission_detail(
    submission_id: int, db, user
) -> RecruiterSubmissionDetailOut:
    """Compatibility wrapper for recruiter submission detail."""
    ensure_recruiter(user)
    sub, task, cs, sim = await recruiter_sub_service.fetch_detail(
        db, submission_id, user.id
    )
    payload = present_detail(sub, task, cs, sim)
    return RecruiterSubmissionDetailOut(**payload)


async def list_submissions(
    db,
    user,
    candidateSessionId: int | None = None,
    taskId: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> RecruiterSubmissionListOut:
    """Compatibility wrapper for recruiter submissions list."""
    ensure_recruiter(user)
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
        payload = present_list_item(sub, task)
        items.append(RecruiterSubmissionListItemOut(**payload))
    return RecruiterSubmissionListOut(items=items)


__all__ = [
    "router",
    "_build_test_results",
    "_parse_diff_summary",
    "_build_diff_url",
    "_redact_text",
    "_truncate_output",
    "_derive_test_status",
    "recruiter_sub_service",
    "ensure_recruiter",
    "get_submission_detail",
    "list_submissions",
]
