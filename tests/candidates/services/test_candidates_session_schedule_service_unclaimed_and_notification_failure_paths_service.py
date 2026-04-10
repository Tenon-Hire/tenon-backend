from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_unclaimed_and_notification_failure_paths(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="schedule-service-errors@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    claimed = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="claimed-errors@test.com",
        status="in_progress",
        candidate_auth0_sub="candidate-claimed-errors@test.com",
        claimed_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    unclaimed = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="unclaimed-errors@test.com",
    )
    await async_session.commit()

    email_service = EmailService(MemoryEmailProvider(), sender="noreply@test.com")
    claimed_principal = _principal(
        claimed.invite_email,
        sub="candidate-claimed-errors@test.com",
        email_verified=True,
    )
    unclaimed_principal = _principal(unclaimed.invite_email)

    with pytest.raises(ApiError) as unclaimed_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=unclaimed.token,
            principal=unclaimed_principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert unclaimed_exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert unclaimed_exc.value.error_code == "SCHEDULE_NOT_CLAIMED"

    trial.day_window_start_local = time(hour=9, minute=0)
    trial.day_window_end_local = time(hour=17, minute=0)
    claimed.schedule_locked_at = None
    claimed.scheduled_start_at = None
    claimed.candidate_timezone = None
    claimed.day_windows_json = None
    await async_session.commit()

    async def _raise_send(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        schedule_service.notification_service,
        "send_schedule_confirmation_emails",
        _raise_send,
    )
    result = await schedule_service.schedule_candidate_session(
        async_session,
        token=claimed.token,
        principal=claimed_principal,
        scheduled_start_at=datetime.now(UTC) + timedelta(days=3),
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=datetime.now(UTC),
    )
    assert result.created is True
    assert result.candidate_session.schedule_locked_at is not None
