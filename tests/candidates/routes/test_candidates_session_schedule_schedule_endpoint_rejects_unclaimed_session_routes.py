from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_schedule_api_utils import *


@pytest.mark.asyncio
async def test_schedule_endpoint_rejects_unclaimed_session(
    async_client, async_session, override_dependencies
):
    _talent_partner, _trial, cs = await _seed_claimed_session(async_session)

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    start_at = _next_local_window_start_utc("America/New_York", days_ahead=1)

    with override_dependencies({get_email_service: lambda: email_service}):
        response = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json={
                "scheduledStartAt": start_at.isoformat().replace("+00:00", "Z"),
                "candidateTimezone": "America/New_York",
            },
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )

    assert response.status_code == 403
    assert response.json()["errorCode"] == "SCHEDULE_NOT_CLAIMED"
    assert len(provider.sent) == 0
