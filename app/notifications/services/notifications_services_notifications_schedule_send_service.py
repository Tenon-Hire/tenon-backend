"""Application module for notifications services notifications schedule send service workflows."""

from __future__ import annotations

from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.schemas.notifications_schemas_notifications_email_schema import (
    EmailSendResult,
)
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.notifications.services.notifications_services_notifications_schedule_content_service import (
    candidate_schedule_confirmation_content,
    talent_partner_schedule_confirmation_content,
)
from app.shared.database.shared_database_models_model import User

_DEFAULT_WINDOW_START = time(hour=9, minute=0)
_DEFAULT_WINDOW_END = time(hour=17, minute=0)


async def _load_talent_partner_email(
    db: AsyncSession, *, talent_partner_id: int | None
) -> str | None:
    if talent_partner_id is None:
        return None
    result = await db.execute(select(User.email).where(User.id == talent_partner_id))
    return result.scalar_one_or_none()


async def send_schedule_confirmation_emails(
    db: AsyncSession,
    *,
    candidate_session,
    trial,
    email_service: EmailService,
    correlation_id: str | None = None,
) -> tuple[EmailSendResult, EmailSendResult | None]:
    """Send schedule confirmation emails."""
    del (
        correlation_id
    )  # Correlation is logged by caller; providers currently do not accept headers.

    scheduled_start_at = getattr(candidate_session, "scheduled_start_at", None)
    candidate_timezone = getattr(candidate_session, "candidate_timezone", None)
    if scheduled_start_at is None or not candidate_timezone:
        return EmailSendResult(status="failed", error="Schedule is incomplete"), None

    window_start = (
        getattr(trial, "day_window_start_local", None) or _DEFAULT_WINDOW_START
    )
    window_end = getattr(trial, "day_window_end_local", None) or _DEFAULT_WINDOW_END

    candidate_email = (
        getattr(candidate_session, "candidate_email", None)
        or getattr(candidate_session, "invite_email", None)
        or ""
    ).strip()
    (
        candidate_subject,
        candidate_text,
        candidate_html,
    ) = candidate_schedule_confirmation_content(
        candidate_name=getattr(candidate_session, "candidate_name", "Candidate"),
        trial_title=getattr(trial, "title", "Trial"),
        role=getattr(trial, "role", "Role"),
        scheduled_start_at_utc=scheduled_start_at,
        timezone_name=candidate_timezone,
        day_window_start_local=window_start,
        day_window_end_local=window_end,
    )
    candidate_result = await email_service.send_email(
        to=candidate_email,
        subject=candidate_subject,
        text=candidate_text,
        html=candidate_html,
    )

    talent_partner_email = await _load_talent_partner_email(
        db, talent_partner_id=getattr(trial, "created_by", None)
    )
    if not talent_partner_email:
        return candidate_result, None

    (
        talent_partner_subject,
        talent_partner_text,
        talent_partner_html,
    ) = talent_partner_schedule_confirmation_content(
        candidate_name=getattr(candidate_session, "candidate_name", "Candidate"),
        candidate_email=candidate_email,
        trial_title=getattr(trial, "title", "Trial"),
        role=getattr(trial, "role", "Role"),
        scheduled_start_at_utc=scheduled_start_at,
        timezone_name=candidate_timezone,
        day_window_start_local=window_start,
        day_window_end_local=window_end,
    )
    talent_partner_result = await email_service.send_email(
        to=talent_partner_email,
        subject=talent_partner_subject,
        text=talent_partner_text,
        html=talent_partner_html,
    )
    return candidate_result, talent_partner_result


__all__ = ["send_schedule_confirmation_emails"]
