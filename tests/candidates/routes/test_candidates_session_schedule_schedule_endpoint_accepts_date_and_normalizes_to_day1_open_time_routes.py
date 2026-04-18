from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from tests.candidates.routes.candidates_session_schedule_api_utils import *


@pytest.mark.asyncio
async def test_schedule_endpoint_accepts_date_and_normalizes_to_day1_open_time(
    async_client, async_session, override_dependencies
):
    talent_partner, _trial, cs = await _seed_claimed_session(async_session)
    await _claim(async_client, cs.token, cs.invite_email)

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    zone = ZoneInfo("America/New_York")
    candidate_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=1)
    expected_start_at = datetime.combine(
        candidate_date, time(hour=9), tzinfo=zone
    ).astimezone(UTC)
    payload = {
        "scheduledStartAt": candidate_date.isoformat(),
        "candidateTimezone": "America/New_York",
        "githubUsername": "octocat",
    }

    with override_dependencies({get_email_service: lambda: email_service}):
        response = await async_client.post(
            f"/api/candidate/session/{cs.token}/schedule",
            json=payload,
            headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scheduledStartAt"] == expected_start_at.isoformat().replace(
        "+00:00", "Z"
    )
    assert len(provider.sent) == 2
    recipients = {message.to for message in provider.sent}
    assert cs.invite_email in recipients
    assert talent_partner.email in recipients
