from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_backfills_day_windows_when_locked(
    async_session, monkeypatch
):
    (
        _tasks,
        candidate_session,
        principal,
        email_service,
    ) = await _seed_claimed_schedule_context(async_session)
    _capture_schedule_notifications(monkeypatch)
    now = datetime.now(UTC)
    start_at = now + timedelta(days=1)

    await schedule_service.schedule_candidate_session(
        async_session,
        token=candidate_session.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=now,
    )

    candidate_session.day_windows_json = None
    await async_session.commit()

    refill = await schedule_service.schedule_candidate_session(
        async_session,
        token=candidate_session.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=now,
    )
    assert refill.created is False
    assert refill.candidate_session.day_windows_json is not None
