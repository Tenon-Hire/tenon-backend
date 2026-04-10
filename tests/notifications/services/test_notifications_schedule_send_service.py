from __future__ import annotations

from datetime import UTC, datetime, time
from types import SimpleNamespace

import pytest

from app.integrations.email.email_provider import MemoryEmailProvider
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.notifications.services.notifications_services_notifications_schedule_send_service import (
    send_schedule_confirmation_emails,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_send_schedule_confirmation_emails_incomplete_schedule(async_session):
    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    candidate_session = SimpleNamespace(
        scheduled_start_at=None,
        candidate_timezone=None,
        candidate_email="candidate@test.com",
        invite_email="candidate@test.com",
        candidate_name="Candidate",
    )
    trial = SimpleNamespace(
        title="Trial",
        role="Backend",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        created_by=None,
    )

    candidate_result, talent_partner_result = await send_schedule_confirmation_emails(
        async_session,
        candidate_session=candidate_session,
        trial=trial,
        email_service=email_service,
    )
    assert candidate_result.status == "failed"
    assert talent_partner_result is None
    assert provider.sent == []


@pytest.mark.asyncio
async def test_send_schedule_confirmation_emails_without_talent_partner(async_session):
    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    candidate_session = SimpleNamespace(
        scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_timezone="America/New_York",
        candidate_email="candidate@test.com",
        invite_email="candidate@test.com",
        candidate_name="Candidate",
    )
    trial = SimpleNamespace(
        title="Trial",
        role="Backend",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        created_by=None,
    )

    candidate_result, talent_partner_result = await send_schedule_confirmation_emails(
        async_session,
        candidate_session=candidate_session,
        trial=trial,
        email_service=email_service,
    )
    assert candidate_result.status == "sent"
    assert talent_partner_result is None
    assert len(provider.sent) == 1
    assert provider.sent[0].to == "candidate@test.com"


@pytest.mark.asyncio
async def test_send_schedule_confirmation_emails_candidate_and_talent_partner(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="talent_partner-sched@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="candidate-sched@test.com",
        candidate_email="candidate-sched@test.com",
    )
    candidate_session.scheduled_start_at = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    candidate_session.candidate_timezone = "America/New_York"
    await async_session.commit()

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")

    candidate_result, talent_partner_result = await send_schedule_confirmation_emails(
        async_session,
        candidate_session=candidate_session,
        trial=trial,
        email_service=email_service,
        correlation_id="req-123",
    )
    assert candidate_result.status == "sent"
    assert talent_partner_result is not None
    assert talent_partner_result.status == "sent"
    assert len(provider.sent) == 2
    recipients = {message.to for message in provider.sent}
    assert "candidate-sched@test.com" in recipients
    assert "talent_partner-sched@test.com" in recipients
