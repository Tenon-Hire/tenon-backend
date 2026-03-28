"""Application module for candidates candidate sessions services candidates candidate sessions schedule service workflows."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_fetch_token_service import (
    fetch_by_token_for_update,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_flow_service import (
    schedule_candidate_session_impl,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_helpers_service import (
    ScheduleCandidateSessionResult,
    _default_window_times,
    _require_claimed_ownership,
    _schedule_matches,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_paths_service import (
    _backfill_locked_schedule as _backfill_locked_schedule_impl,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_paths_service import (
    _set_new_schedule as _set_new_schedule_impl,
)
from app.notifications.services import service as notification_service
from app.shared.auth.principal import Principal

logger = logging.getLogger(__name__)


async def _backfill_locked_schedule(db, **kwargs):
    return await _backfill_locked_schedule_impl(
        db, schedule_matches=_schedule_matches, **kwargs
    )


async def _set_new_schedule(db, **kwargs):
    return await _set_new_schedule_impl(db, **kwargs)


async def schedule_candidate_session(
    db: AsyncSession,
    *,
    token: str,
    principal: Principal,
    scheduled_start_at: datetime,
    candidate_timezone: str,
    email_service,
    now: datetime | None = None,
    correlation_id: str | None = None,
) -> ScheduleCandidateSessionResult:
    """Schedule candidate session."""
    return await schedule_candidate_session_impl(
        db,
        token=token,
        principal=principal,
        scheduled_start_at=scheduled_start_at,
        candidate_timezone=candidate_timezone,
        email_service=email_service,
        now=now,
        correlation_id=correlation_id,
        fetch_by_token_for_update=fetch_by_token_for_update,
        require_claimed_ownership=_require_claimed_ownership,
        backfill_locked_schedule=_backfill_locked_schedule,
        set_new_schedule=_set_new_schedule,
        send_schedule_confirmation_emails=notification_service.send_schedule_confirmation_emails,
        result_type=ScheduleCandidateSessionResult,
        logger=logger,
    )


__all__ = [
    "ScheduleCandidateSessionResult",
    "_default_window_times",
    "_require_claimed_ownership",
    "_schedule_matches",
    "schedule_candidate_session",
]
