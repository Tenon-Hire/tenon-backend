"""Application module for notifications services notifications invite rate limit service workflows."""

from __future__ import annotations

from datetime import datetime

from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailSendResult,
)
from app.notifications.services.notifications_services_notifications_invite_time_service import (
    INVITE_EMAIL_RATE_LIMIT_SECONDS,
    rate_limited,
)


def should_rate_limit(candidate_session, now: datetime) -> bool:
    """Return whether rate limit."""
    return rate_limited(
        candidate_session.invite_email_last_attempt_at,
        now,
        INVITE_EMAIL_RATE_LIMIT_SECONDS,
    )


async def record_rate_limit(db, candidate_session, now: datetime) -> EmailSendResult:
    """Record rate limit."""
    candidate_session.invite_email_status = "rate_limited"
    candidate_session.invite_email_last_attempt_at = now
    candidate_session.invite_email_error = "Rate limited"
    await db.commit()
    return EmailSendResult(status="rate_limited", error="Rate limited")
