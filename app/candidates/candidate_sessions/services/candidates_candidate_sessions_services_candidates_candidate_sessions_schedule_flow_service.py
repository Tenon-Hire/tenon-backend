"""Application module for candidates candidate sessions services candidates candidate sessions schedule flow service workflows."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    coerce_utc_datetime,
    validate_timezone,
)
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.shared.utils.shared_utils_errors_utils import (
    INVITE_TOKEN_EXPIRED,
    SCHEDULE_INVALID_TIMEZONE,
    SCHEDULE_INVALID_WINDOW,
    SCHEDULE_START_IN_PAST,
    ApiError,
)


async def schedule_candidate_session_impl(
    db,
    *,
    token: str,
    principal,
    scheduled_start_at: datetime,
    candidate_timezone: str,
    email_service,
    now: datetime | None,
    correlation_id: str | None,
    fetch_by_token_for_update,
    require_claimed_ownership,
    backfill_locked_schedule,
    set_new_schedule,
    send_schedule_confirmation_emails,
    result_type,
    logger,
):
    """Schedule candidate session impl."""
    resolved_now = coerce_utc_datetime(now or shared_utcnow())
    scheduled_start_at_utc = coerce_utc_datetime(scheduled_start_at).replace(
        microsecond=0
    )
    if scheduled_start_at_utc < resolved_now:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scheduled start must be in the future.",
            error_code=SCHEDULE_START_IN_PAST,
            retryable=False,
        )
    try:
        normalized_timezone = validate_timezone((candidate_timezone or "").strip())
    except ValueError as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Candidate timezone must be a valid IANA timezone.",
            error_code=SCHEDULE_INVALID_TIMEZONE,
            retryable=False,
        ) from exc
    try:
        candidate_session = await fetch_by_token_for_update(db, token, now=resolved_now)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_410_GONE:
            raise ApiError(
                status_code=status.HTTP_410_GONE,
                detail=str(exc.detail),
                error_code=INVITE_TOKEN_EXPIRED,
                retryable=False,
            ) from exc
        raise
    changed = require_claimed_ownership(candidate_session, principal)
    schedule_created = False
    trial_for_email = None
    if getattr(candidate_session, "schedule_locked_at", None) is not None:
        changed = (
            await backfill_locked_schedule(
                db,
                candidate_session=candidate_session,
                scheduled_start_at_utc=scheduled_start_at_utc,
                normalized_timezone=normalized_timezone,
            )
            or changed
        )
    else:
        try:
            trial_for_email = await set_new_schedule(
                db,
                candidate_session=candidate_session,
                scheduled_start_at_utc=scheduled_start_at_utc,
                normalized_timezone=normalized_timezone,
                resolved_now=resolved_now,
            )
        except ValueError as exc:
            raise ApiError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unable to derive schedule day windows.",
                error_code=SCHEDULE_INVALID_WINDOW,
                retryable=False,
            ) from exc
        changed = True
        schedule_created = True
    if changed:
        await db.commit()
    if schedule_created:
        logger.info(
            "Candidate schedule set candidateSessionId=%s candidateTimezone=%s scheduledStartAt=%s correlationId=%s",
            candidate_session.id,
            normalized_timezone,
            scheduled_start_at_utc.isoformat(),
            correlation_id or "",
        )
        try:
            await send_schedule_confirmation_emails(
                db,
                candidate_session=candidate_session,
                trial=trial_for_email,
                email_service=email_service,
                correlation_id=correlation_id,
            )
        except Exception:
            logger.exception(
                "Schedule confirmation email dispatch failed candidateSessionId=%s correlationId=%s",
                candidate_session.id,
                correlation_id or "",
            )
    return result_type(candidate_session=candidate_session, created=schedule_created)


__all__ = ["schedule_candidate_session_impl"]
