"""Application module for notifications services notifications invite send service workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailSendResult,
    EmailService,
)
from app.notifications.services.notifications_services_notifications_invite_dispatch_service import (
    dispatch_invite_email,
    record_send_result,
)
from app.notifications.services.notifications_services_notifications_invite_rate_limit_service import (
    record_rate_limit,
    should_rate_limit,
)
from app.notifications.services.notifications_services_notifications_invite_time_service import (
    utc_now,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
)


async def send_invite_email(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    trial: Trial,
    invite_url: str,
    email_service: EmailService,
    now: datetime | None = None,
) -> EmailSendResult:
    """Send invite email."""
    resolved_now = utc_now(now)
    if should_rate_limit(candidate_session, resolved_now):
        return await record_rate_limit(db, candidate_session, resolved_now)

    result = await dispatch_invite_email(
        email_service,
        candidate_session=candidate_session,
        trial=trial,
        invite_url=invite_url,
    )
    return await record_send_result(db, candidate_session, resolved_now, result)
