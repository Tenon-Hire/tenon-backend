from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_schedule_api_utils import *


@pytest.mark.asyncio
async def test_schedule_endpoint_rejects_invalid_timezone_and_past(
    async_client, async_session, override_dependencies
):
    _talent_partner, _trial, cs = await _seed_claimed_session(async_session)
    await _claim(async_client, cs.token, cs.invite_email)

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    future_start = _next_local_window_start_utc("America/New_York", days_ahead=1)
    past_start = datetime.now(UTC) - timedelta(days=1)

    with override_dependencies({get_email_service: lambda: email_service}):
        invalid_tz = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json={
                "scheduledStartAt": future_start.isoformat().replace("+00:00", "Z"),
                "candidateTimezone": "Invalid/Timezone",
            },
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )
        past = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json={
                "scheduledStartAt": past_start.isoformat().replace("+00:00", "Z"),
                "candidateTimezone": "America/New_York",
            },
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )

    assert invalid_tz.status_code == 422
    assert invalid_tz.json()["errorCode"] == "SCHEDULE_INVALID_TIMEZONE"

    assert past.status_code == 422
    assert past.json()["errorCode"] == "SCHEDULE_START_IN_PAST"
    assert len(provider.sent) == 0
