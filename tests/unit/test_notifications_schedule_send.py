from __future__ import annotations

from datetime import UTC, datetime, time
from types import SimpleNamespace

import pytest

from app.integrations.notifications.email_provider import MemoryEmailProvider
from app.services.email import EmailService
from app.services.notifications.schedule_send import send_schedule_confirmation_emails
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
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
    simulation = SimpleNamespace(
        title="Simulation",
        role="Backend",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        created_by=None,
    )

    candidate_result, recruiter_result = await send_schedule_confirmation_emails(
        async_session,
        candidate_session=candidate_session,
        simulation=simulation,
        email_service=email_service,
    )
    assert candidate_result.status == "failed"
    assert recruiter_result is None
    assert provider.sent == []


@pytest.mark.asyncio
async def test_send_schedule_confirmation_emails_without_recruiter(async_session):
    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    candidate_session = SimpleNamespace(
        scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_timezone="America/New_York",
        candidate_email="candidate@test.com",
        invite_email="candidate@test.com",
        candidate_name="Candidate",
    )
    simulation = SimpleNamespace(
        title="Simulation",
        role="Backend",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        created_by=None,
    )

    candidate_result, recruiter_result = await send_schedule_confirmation_emails(
        async_session,
        candidate_session=candidate_session,
        simulation=simulation,
        email_service=email_service,
    )
    assert candidate_result.status == "sent"
    assert recruiter_result is None
    assert len(provider.sent) == 1
    assert provider.sent[0].to == "candidate@test.com"


@pytest.mark.asyncio
async def test_send_schedule_confirmation_emails_candidate_and_recruiter(async_session):
    recruiter = await create_recruiter(async_session, email="recruiter-sched@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="candidate-sched@test.com",
        candidate_email="candidate-sched@test.com",
    )
    candidate_session.scheduled_start_at = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    candidate_session.candidate_timezone = "America/New_York"
    await async_session.commit()

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")

    candidate_result, recruiter_result = await send_schedule_confirmation_emails(
        async_session,
        candidate_session=candidate_session,
        simulation=simulation,
        email_service=email_service,
        correlation_id="req-123",
    )
    assert candidate_result.status == "sent"
    assert recruiter_result is not None
    assert recruiter_result.status == "sent"
    assert len(provider.sent) == 2
    recipients = {message.to for message in provider.sent}
    assert "candidate-sched@test.com" in recipients
    assert "recruiter-sched@test.com" in recipients
