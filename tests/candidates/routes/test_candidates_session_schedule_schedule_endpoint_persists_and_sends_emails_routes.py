from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_schedule_api_utils import *


@pytest.mark.asyncio
async def test_schedule_endpoint_persists_and_sends_emails(
    async_client, async_session, override_dependencies
):
    talent_partner, trial, cs = await _seed_claimed_session(async_session)
    await _claim(async_client, cs.token, cs.invite_email)

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    start_at = _next_local_window_start_utc("America/New_York", days_ahead=1)
    payload = {
        "scheduledStartAt": start_at.isoformat().replace("+00:00", "Z"),
        "candidateTimezone": "America/New_York",
    }

    with override_dependencies({get_email_service: lambda: email_service}):
        response = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json=payload,
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidateSessionId"] == cs.id
    assert body["candidateTimezone"] == "America/New_York"
    assert body["scheduledStartAt"] == payload["scheduledStartAt"]
    assert len(body["dayWindows"]) == 5
    assert body["scheduleLockedAt"] is not None

    await async_session.refresh(cs)
    assert cs.scheduled_start_at is not None
    assert cs.candidate_timezone == "America/New_York"
    assert cs.schedule_locked_at is not None
    assert cs.day_windows_json is not None

    assert len(provider.sent) == 2
    recipients = {message.to for message in provider.sent}
    assert cs.invite_email in recipients
    assert talent_partner.email in recipients
    assert any("Schedule confirmed" in message.subject for message in provider.sent)
