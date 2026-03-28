from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_idempotent_retry_does_not_resend_or_duplicate_jobs(
    async_session, monkeypatch
):
    (
        _tasks,
        candidate_session,
        principal,
        email_service,
    ) = await _seed_claimed_schedule_context(async_session)
    sent_events = _capture_schedule_notifications(monkeypatch)
    now = datetime.now(UTC)
    start_at = now + timedelta(days=1)

    first = await schedule_service.schedule_candidate_session(
        async_session,
        token=candidate_session.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=now,
        correlation_id="req-1",
    )
    assert first.created is True

    second = await schedule_service.schedule_candidate_session(
        async_session,
        token=candidate_session.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=now,
    )
    assert second.created is False
    assert sent_events == [(candidate_session.id, "req-1")]

    finalize_jobs = await _list_jobs(
        async_session,
        candidate_session_id=candidate_session.id,
        job_type="day_close_finalize_text",
    )
    enforcement_jobs = await _list_jobs(
        async_session,
        candidate_session_id=candidate_session.id,
        job_type="day_close_enforcement",
    )
    assert len(finalize_jobs) == 2
    assert len(enforcement_jobs) == 2
