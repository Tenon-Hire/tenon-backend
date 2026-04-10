from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_schedule_api_utils import *


@pytest.mark.asyncio
async def test_schedule_endpoint_idempotent_and_conflict(
    async_client, async_session, override_dependencies
):
    _talent_partner, _trial, cs = await _seed_claimed_session(async_session)
    await _claim(async_client, cs.token, cs.invite_email)

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    start_at = _next_local_window_start_utc("America/New_York", days_ahead=2)
    payload = {
        "scheduledStartAt": start_at.isoformat().replace("+00:00", "Z"),
        "candidateTimezone": "America/New_York",
    }

    with override_dependencies({get_email_service: lambda: email_service}):
        first = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json=payload,
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )
        assert first.status_code == 200, first.text
        assert len(provider.sent) == 2
        second = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json=payload,
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )

        conflict_payload = {
            "scheduledStartAt": (start_at + timedelta(days=1))
            .isoformat()
            .replace("+00:00", "Z"),
            "candidateTimezone": "America/New_York",
        }
        conflict = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json=conflict_payload,
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )

    assert second.status_code == 200, second.text
    assert first.json() == second.json()
    assert len(provider.sent) == 2

    assert conflict.status_code == 409
    assert conflict.json()["errorCode"] == "SCHEDULE_ALREADY_SET"
