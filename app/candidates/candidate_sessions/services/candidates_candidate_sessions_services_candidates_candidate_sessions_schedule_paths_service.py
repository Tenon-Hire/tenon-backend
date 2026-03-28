"""Application module for candidates candidate sessions services candidates candidate sessions schedule paths service workflows."""

from __future__ import annotations

from fastapi import status

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_service import (
    enqueue_day_close_jobs,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_windows_service import (
    _derive_serialized_day_windows,
)
from app.shared.utils.shared_utils_errors_utils import SCHEDULE_ALREADY_SET, ApiError


async def _backfill_locked_schedule(
    db,
    *,
    candidate_session,
    scheduled_start_at_utc,
    normalized_timezone: str,
    schedule_matches,
) -> bool:
    if not schedule_matches(
        candidate_session=candidate_session,
        scheduled_start_at=scheduled_start_at_utc,
        candidate_timezone=normalized_timezone,
    ):
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Schedule has already been set for this session.",
            error_code=SCHEDULE_ALREADY_SET,
            retryable=False,
        )
    if getattr(candidate_session, "day_windows_json", None):
        return False
    candidate_session.day_windows_json = _derive_serialized_day_windows(
        simulation=candidate_session.simulation,
        scheduled_start_at_utc=scheduled_start_at_utc,
        normalized_timezone=normalized_timezone,
    )
    await enqueue_day_close_jobs(db, candidate_session=candidate_session, commit=False)
    return True


async def _set_new_schedule(
    db,
    *,
    candidate_session,
    scheduled_start_at_utc,
    normalized_timezone: str,
    resolved_now,
) -> object:
    candidate_session.scheduled_start_at = scheduled_start_at_utc
    candidate_session.candidate_timezone = normalized_timezone
    candidate_session.day_windows_json = _derive_serialized_day_windows(
        simulation=candidate_session.simulation,
        scheduled_start_at_utc=scheduled_start_at_utc,
        normalized_timezone=normalized_timezone,
    )
    candidate_session.schedule_locked_at = resolved_now
    await enqueue_day_close_jobs(db, candidate_session=candidate_session, commit=False)
    return candidate_session.simulation


__all__ = ["_backfill_locked_schedule", "_set_new_schedule"]
