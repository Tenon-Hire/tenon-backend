from __future__ import annotations

# helper import baseline for restructure-compat
import re
from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy import select

from app.candidates.candidate_sessions.services import schedule as schedule_service
from app.config import settings
from app.integrations.email.email_provider import MemoryEmailProvider
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import Job
from app.shared.utils.shared_utils_errors_utils import ApiError
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _principal(
    email: str,
    *,
    sub: str | None = None,
    email_verified: bool | None = True,
) -> Principal:
    email_claim = settings.auth.AUTH0_EMAIL_CLAIM
    permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
    claims = {
        "sub": sub or f"candidate-{email}",
        "email": email,
        email_claim: email,
        "permissions": ["candidate:access"],
        permissions_claim: ["candidate:access"],
    }
    if email_verified is not None:
        claims["email_verified"] = email_verified
    return Principal(
        sub=sub or f"candidate-{email}",
        email=email,
        name=email.split("@")[0] if email else "",
        roles=[],
        permissions=["candidate:access"],
        claims=claims,
    )


async def _seed_claimed_schedule_context(
    async_session,
    *,
    talent_partner_email: str = "schedule-service@test.com",
    invite_email: str = "claimed-schedule@test.com",
    candidate_sub: str = "candidate-claimed-schedule@test.com",
):
    talent_partner = await create_talent_partner(
        async_session, email=talent_partner_email
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email=invite_email,
        status="in_progress",
        candidate_auth0_sub=candidate_sub,
        candidate_email=None,
        claimed_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    await async_session.commit()
    principal = _principal(invite_email, sub=candidate_sub, email_verified=True)
    email_service = EmailService(MemoryEmailProvider(), sender="noreply@test.com")
    return tasks, candidate_session, principal, email_service


def _capture_schedule_notifications(monkeypatch):
    sent_events: list[tuple[int, str | None]] = []

    async def _fake_send(*_args, candidate_session, correlation_id=None, **_kwargs):
        sent_events.append((candidate_session.id, correlation_id))
        return None, None

    monkeypatch.setattr(
        schedule_service.notification_service,
        "send_schedule_confirmation_emails",
        _fake_send,
    )
    return sent_events


async def _list_jobs(async_session, *, candidate_session_id: int, job_type: str):
    query = select(Job).where(
        Job.job_type == job_type,
        Job.candidate_session_id == candidate_session_id,
    )
    return list((await async_session.execute(query)).scalars())


__all__ = [name for name in globals() if not name.startswith("__")]
