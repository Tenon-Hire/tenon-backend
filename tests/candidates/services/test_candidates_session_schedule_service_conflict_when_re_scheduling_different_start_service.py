from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_conflict_when_re_scheduling_different_start(
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

    with pytest.raises(ApiError) as excinfo:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=candidate_session.token,
            principal=principal,
            scheduled_start_at=start_at + timedelta(days=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=now,
        )
    assert excinfo.value.status_code == status.HTTP_409_CONFLICT
    assert excinfo.value.error_code == "SCHEDULE_ALREADY_SET"
