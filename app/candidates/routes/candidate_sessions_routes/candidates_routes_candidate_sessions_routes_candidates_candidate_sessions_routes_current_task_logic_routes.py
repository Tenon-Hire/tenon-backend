"""Logic helper for current task route."""

from fastapi import status

from app.candidates.candidate_sessions import services as cs_service
from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_rate_limits_routes import (
    CANDIDATE_CURRENT_TASK_RATE_LIMIT,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_responses_routes import (
    build_current_task_response,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_time_utils import (
    utcnow,
)
from app.shared.auth import rate_limit
from app.shared.utils.shared_utils_errors_utils import ApiError


def _require_candidate_session_header_match(candidate_session_id: int, request) -> None:
    header_value = (request.headers.get("x-candidate-session-id") or "").strip()
    if not header_value:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing candidate session headers",
            error_code="CANDIDATE_SESSION_HEADER_REQUIRED",
        )
    try:
        header_session_id = int(header_value)
    except ValueError as exc:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing candidate session headers",
            error_code="CANDIDATE_SESSION_HEADER_REQUIRED",
        ) from exc
    if header_session_id < 1:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing candidate session headers",
            error_code="CANDIDATE_SESSION_HEADER_REQUIRED",
        )
    if header_session_id != candidate_session_id:
        raise ApiError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate session header does not match requested session.",
            error_code="CANDIDATE_SESSION_HEADER_MISMATCH",
            retryable=False,
        )


async def build_current_task_view(candidate_session_id, request, principal, db):
    """Build current task view."""
    _require_candidate_session_header_match(candidate_session_id, request)
    if rate_limit.rate_limit_enabled():
        key = rate_limit.rate_limit_key(
            "candidate_current_task",
            str(candidate_session_id),
            rate_limit.client_id(request),
        )
        rate_limit.limiter.allow(key, CANDIDATE_CURRENT_TASK_RATE_LIMIT)
    now = utcnow()
    cs = await cs_service.fetch_owned_session(
        db, candidate_session_id, principal, now=now
    )
    cs_service.ensure_schedule_started_for_content(cs, now=now)
    (
        _tasks,
        completed_ids,
        current_task,
        completed,
        total,
        is_complete,
    ) = await cs_service.progress_snapshot(db, cs, now=now)
    if is_complete and cs.status != "completed":
        cs.status = "completed"
        if cs.completed_at is None:
            cs.completed_at = now
        await db.commit()
        await db.refresh(cs)
    day_audit = None
    if not is_complete and current_task is not None:
        day_audit = await cs_repo.get_day_audit(
            db,
            candidate_session_id=cs.id,
            day_index=current_task.day_index,
        )
    return build_current_task_response(
        cs,
        current_task,
        completed_ids,
        completed,
        total,
        is_complete,
        day_audit=day_audit,
        now_utc=now,
    )


__all__ = ["build_current_task_view"]
