from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_validation_errors(async_session):
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
    await async_session.commit()

    email_service = EmailService(MemoryEmailProvider(), sender="noreply@test.com")
    claimed_principal = _principal(
        claimed.invite_email,
        sub="candidate-claimed-errors@test.com",
        email_verified=True,
    )

    with pytest.raises(ApiError) as past_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=claimed.token,
            principal=claimed_principal,
            scheduled_start_at=datetime.now(UTC) - timedelta(minutes=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert past_exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert past_exc.value.error_code == "SCHEDULE_START_IN_PAST"

    with pytest.raises(ApiError) as tz_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=claimed.token,
            principal=claimed_principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
            candidate_timezone="Bad/Timezone",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert tz_exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert tz_exc.value.error_code == "SCHEDULE_INVALID_TIMEZONE"

    trial.day_window_start_local = time(hour=17, minute=0)
    trial.day_window_end_local = time(hour=9, minute=0)
    await async_session.commit()
    with pytest.raises(ApiError) as window_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=claimed.token,
            principal=claimed_principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=2),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert window_exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert window_exc.value.error_code == "SCHEDULE_INVALID_WINDOW"
