from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.principal import Principal
from app.core.errors import (
    CANDIDATE_AUTH_EMAIL_MISSING,
    CANDIDATE_INVITE_EMAIL_MISMATCH,
    CANDIDATE_SESSION_ALREADY_CLAIMED,
    INVITE_TOKEN_EXPIRED,
    SCHEDULE_ALREADY_SET,
    SCHEDULE_INVALID_TIMEZONE,
    SCHEDULE_INVALID_WINDOW,
    SCHEDULE_NOT_CLAIMED,
    SCHEDULE_START_IN_PAST,
    ApiError,
)
from app.domains.notifications import service as notification_service
from app.services.candidate_sessions.day_close_jobs import (
    enqueue_day_close_finalize_text_jobs,
)
from app.services.candidate_sessions.email import normalize_email
from app.services.candidate_sessions.fetch_token import fetch_by_token_for_update
from app.services.candidate_sessions.ownership import ensure_email_verified
from app.services.email import EmailService
from app.services.scheduling.day_windows import (
    coerce_utc_datetime,
    derive_day_windows,
    serialize_day_windows,
    validate_timezone,
)

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW_START = time(hour=9, minute=0)
_DEFAULT_WINDOW_END = time(hour=17, minute=0)


@dataclass(slots=True)
class ScheduleCandidateSessionResult:
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
    ensure_email_verified(principal)
    email = normalize_email(principal.email)
    if not email:
        _forbidden(
            "Authenticated email claim is missing.",
            CANDIDATE_AUTH_EMAIL_MISSING,
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
        _forbidden(
            "Invite must be claimed before scheduling.",
            SCHEDULE_NOT_CLAIMED,
        )
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
    *,
    candidate_session,
    scheduled_start_at: datetime,
    candidate_timezone: str,
) -> bool:
    existing_start = getattr(candidate_session, "scheduled_start_at", None)
    if existing_start is None:
        return False
    existing_timezone_raw = (
        getattr(candidate_session, "candidate_timezone", None) or ""
    ).strip()
    if not existing_timezone_raw:
        return False

    existing_start_normalized = coerce_utc_datetime(existing_start).replace(
        microsecond=0
    )
    incoming_start_normalized = coerce_utc_datetime(scheduled_start_at).replace(
        microsecond=0
    )
    return (
        existing_start_normalized == incoming_start_normalized
        and existing_timezone_raw == candidate_timezone
    )


def _default_window_times(simulation) -> tuple[time, time]:
    start_local = (
        getattr(simulation, "day_window_start_local", None) or _DEFAULT_WINDOW_START
    )
    end_local = getattr(simulation, "day_window_end_local", None) or _DEFAULT_WINDOW_END
    return start_local, end_local


async def schedule_candidate_session(
    db: AsyncSession,
    *,
    token: str,
    principal: Principal,
    scheduled_start_at: datetime,
    candidate_timezone: str,
    email_service: EmailService,
    now: datetime | None = None,
    correlation_id: str | None = None,
) -> ScheduleCandidateSessionResult:
    resolved_now = coerce_utc_datetime(now or datetime.now(UTC))
    scheduled_start_at_utc = coerce_utc_datetime(scheduled_start_at).replace(
        microsecond=0
    )
    candidate_timezone = (candidate_timezone or "").strip()
    if scheduled_start_at_utc < resolved_now:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scheduled start must be in the future.",
            error_code=SCHEDULE_START_IN_PAST,
            retryable=False,
        )

    try:
        normalized_timezone = validate_timezone(candidate_timezone)
    except ValueError as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Candidate timezone must be a valid IANA timezone.",
            error_code=SCHEDULE_INVALID_TIMEZONE,
            retryable=False,
        ) from exc

    schedule_created = False
    changed = False
    candidate_session = None
    simulation_for_email = None

    async with db.begin_nested():
        try:
            candidate_session = await fetch_by_token_for_update(
                db, token, now=resolved_now
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_410_GONE:
                # Repo convention: expired invite tokens surface as HTTP 410.
                # This endpoint keeps that status and adds INVITE_TOKEN_EXPIRED for machine handling.
                raise ApiError(
                    status_code=status.HTTP_410_GONE,
                    detail=str(exc.detail),
                    error_code=INVITE_TOKEN_EXPIRED,
                    retryable=False,
                ) from exc
            raise
        changed = _require_claimed_ownership(candidate_session, principal)

        lock_timestamp = getattr(candidate_session, "schedule_locked_at", None)
        if lock_timestamp is not None:
            if not _schedule_matches(
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
            if not getattr(candidate_session, "day_windows_json", None):
                simulation = candidate_session.simulation
                window_start, window_end = _default_window_times(simulation)
                day_windows = derive_day_windows(
                    scheduled_start_at_utc=scheduled_start_at_utc,
                    candidate_tz=normalized_timezone,
                    day_window_start_local=window_start,
                    day_window_end_local=window_end,
                    overrides=getattr(simulation, "day_window_overrides_json", None),
                    overrides_enabled=bool(
                        getattr(simulation, "day_window_overrides_enabled", False)
                    ),
                    total_days=5,
                )
                candidate_session.day_windows_json = serialize_day_windows(day_windows)
                changed = True
                await enqueue_day_close_finalize_text_jobs(
                    db,
                    candidate_session=candidate_session,
                    commit=False,
                )
        else:
            simulation = candidate_session.simulation
            window_start, window_end = _default_window_times(simulation)
            try:
                day_windows = derive_day_windows(
                    scheduled_start_at_utc=scheduled_start_at_utc,
                    candidate_tz=normalized_timezone,
                    day_window_start_local=window_start,
                    day_window_end_local=window_end,
                    overrides=getattr(simulation, "day_window_overrides_json", None),
                    overrides_enabled=bool(
                        getattr(simulation, "day_window_overrides_enabled", False)
                    ),
                    total_days=5,
                )
            except ValueError as exc:
                raise ApiError(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Unable to derive schedule day windows.",
                    error_code=SCHEDULE_INVALID_WINDOW,
                    retryable=False,
                ) from exc

            candidate_session.scheduled_start_at = scheduled_start_at_utc
            candidate_session.candidate_timezone = normalized_timezone
            candidate_session.day_windows_json = serialize_day_windows(day_windows)
            candidate_session.schedule_locked_at = resolved_now
            simulation_for_email = simulation
            changed = True
            schedule_created = True
            await enqueue_day_close_finalize_text_jobs(
                db,
                candidate_session=candidate_session,
                commit=False,
            )

    if changed:
        await db.commit()
        await db.refresh(candidate_session)

    if schedule_created:
        logger.info(
            "Candidate schedule set candidateSessionId=%s candidateTimezone=%s scheduledStartAt=%s correlationId=%s",
            candidate_session.id,
            normalized_timezone,
            scheduled_start_at_utc.isoformat(),
            correlation_id or "",
        )
        try:
            await notification_service.send_schedule_confirmation_emails(
                db,
                candidate_session=candidate_session,
                simulation=simulation_for_email,
                email_service=email_service,
                correlation_id=correlation_id,
            )
        except Exception:
            logger.exception(
                "Schedule confirmation email dispatch failed candidateSessionId=%s correlationId=%s",
                candidate_session.id,
                correlation_id or "",
            )

    return ScheduleCandidateSessionResult(
        candidate_session=candidate_session,
        created=schedule_created,
    )


__all__ = ["ScheduleCandidateSessionResult", "schedule_candidate_session"]
