"""Application module for candidates candidate sessions services candidates candidate sessions schedule helpers service workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from fastapi import status

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_email_service import (
    normalize_email,
)
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    coerce_utc_datetime,
)
from app.shared.auth.principal import Principal
from app.shared.utils.shared_utils_errors_utils import (
    CANDIDATE_AUTH_EMAIL_MISSING,
    CANDIDATE_INVITE_EMAIL_MISMATCH,
    CANDIDATE_SESSION_ALREADY_CLAIMED,
    SCHEDULE_NOT_CLAIMED,
    ApiError,
)

DEFAULT_WINDOW_START = time(hour=9, minute=0)
DEFAULT_WINDOW_END = time(hour=17, minute=0)


@dataclass(slots=True)
class ScheduleCandidateSessionResult:
    """Represent schedule candidate session result data and behavior."""

    candidate_session: object
    created: bool


def _forbidden(detail: str, error_code: str) -> None:
    raise ApiError(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
        error_code=error_code,
        retryable=False,
    )


def _require_claimed_ownership(candidate_session, principal: Principal) -> bool:
    email = normalize_email(principal.email)
    if not email:
        _forbidden(
            "Authenticated email claim is missing.", CANDIDATE_AUTH_EMAIL_MISSING
        )
    invite_email = normalize_email(candidate_session.invite_email)
    if invite_email != email:
        _forbidden(
            "Invite email does not match authenticated user.",
            CANDIDATE_INVITE_EMAIL_MISMATCH,
        )
    stored_sub = getattr(candidate_session, "candidate_auth0_sub", None)
    claimed_at = getattr(candidate_session, "claimed_at", None)
    if not stored_sub or claimed_at is None:
        _forbidden("Invite must be claimed before scheduling.", SCHEDULE_NOT_CLAIMED)
    if stored_sub != principal.sub:
        _forbidden(
            "Candidate session is already claimed by another user.",
            CANDIDATE_SESSION_ALREADY_CLAIMED,
        )
    changed = False
    if getattr(candidate_session, "candidate_auth0_email", None) != email:
        candidate_session.candidate_auth0_email = email
        changed = True
    if candidate_session.candidate_email != email:
        candidate_session.candidate_email = email
        changed = True
    return changed


def _schedule_matches(
    *, candidate_session, scheduled_start_at: datetime, candidate_timezone: str
) -> bool:
    existing_start = getattr(candidate_session, "scheduled_start_at", None)
    if existing_start is None:
        return False
    existing_timezone = (
        getattr(candidate_session, "candidate_timezone", None) or ""
    ).strip()
    if not existing_timezone:
        return False
    existing_start_normalized = coerce_utc_datetime(existing_start).replace(
        microsecond=0
    )
    incoming_start_normalized = coerce_utc_datetime(scheduled_start_at).replace(
        microsecond=0
    )
    return (
        existing_start_normalized == incoming_start_normalized
        and existing_timezone == candidate_timezone
    )


def _default_window_times(trial) -> tuple[time, time]:
    start_local = getattr(trial, "day_window_start_local", None) or DEFAULT_WINDOW_START
    end_local = getattr(trial, "day_window_end_local", None) or DEFAULT_WINDOW_END
    return start_local, end_local


__all__ = [
    "ScheduleCandidateSessionResult",
    "_default_window_times",
    "_require_claimed_ownership",
    "_schedule_matches",
]
