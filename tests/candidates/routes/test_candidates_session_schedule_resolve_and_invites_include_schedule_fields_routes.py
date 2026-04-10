from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_schedule_api_utils import *


@pytest.mark.asyncio
async def test_resolve_and_invites_include_schedule_fields(
    async_client, async_session, override_dependencies
):
    _talent_partner, _trial, cs = await _seed_claimed_session(async_session)
    await _claim(async_client, cs.token, cs.invite_email)

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    start_at = _next_local_window_start_utc("America/New_York", days_ahead=1)
    schedule_payload = {
        "scheduledStartAt": start_at.isoformat().replace("+00:00", "Z"),
        "candidateTimezone": "America/New_York",
    }

    with override_dependencies({get_email_service: lambda: email_service}):
        schedule_response = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json=schedule_payload,
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )
    assert schedule_response.status_code == 200, schedule_response.text

    resolve = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert resolve.status_code == 200, resolve.text
    resolve_body = resolve.json()
    assert resolve_body["scheduledStartAt"] == schedule_payload["scheduledStartAt"]
    assert resolve_body["candidateTimezone"] == "America/New_York"
    assert len(resolve_body["dayWindows"]) == 5
    assert resolve_body["scheduleLockedAt"] is not None
    assert resolve_body["currentDayWindow"] is not None
    assert resolve_body["currentDayWindow"]["dayIndex"] == 1

    invites = await async_client.get(
        "/api/candidate/invites",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert invites.status_code == 200, invites.text
    invite_items = invites.json()
    assert len(invite_items) == 1
    assert invite_items[0]["candidateSessionId"] == cs.id
    assert invite_items[0]["scheduledStartAt"] == schedule_payload["scheduledStartAt"]
    assert invite_items[0]["candidateTimezone"] == "America/New_York"
    assert len(invite_items[0]["dayWindows"]) == 5
    assert invite_items[0]["scheduleLockedAt"] is not None
    assert invite_items[0]["currentDayWindow"] is not None

    refreshed = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs.id)
        )
    ).scalar_one()
    assert refreshed.schedule_locked_at is not None
