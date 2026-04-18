from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_rejects_local_past_date(
    async_session,
):
    (
        _tasks,
        candidate_session,
        principal,
        email_service,
    ) = await _seed_claimed_schedule_context(async_session)
    now = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)

    with pytest.raises(ApiError) as excinfo:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=candidate_session.token,
            principal=principal,
            scheduled_start_at=date(2026, 3, 10),
            candidate_timezone="America/New_York",
            github_username="octocat",
            email_service=email_service,
            now=now,
        )

    assert excinfo.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert excinfo.value.error_code == "SCHEDULE_START_IN_PAST"
