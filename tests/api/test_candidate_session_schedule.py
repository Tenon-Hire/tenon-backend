from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.api.dependencies.notifications import get_email_service
from app.domains import CandidateSession
from app.integrations.notifications.email_provider import MemoryEmailProvider
from app.main import app
from app.services.email import EmailService
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _next_local_window_start_utc(
    timezone_name: str, *, days_ahead: int = 1
) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=days_ahead)
    local_start = datetime.combine(local_date, time(hour=9, minute=0), tzinfo=zone)
    return local_start.astimezone(UTC)


async def _seed_claimed_session(async_session):
    recruiter = await create_recruiter(
        async_session, email="schedule-recruiter@test.com"
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="schedule-candidate@test.com",
    )
    await async_session.commit()
    return recruiter, simulation, candidate_session


async def _claim(async_client, token: str, email: str):
    response = await async_client.post(
        f"/api/candidate/session/{token}/claim",
        headers={"Authorization": f"Bearer candidate:{email}"},
    )
    assert response.status_code == 200, response.text


def test_schedule_route_registered_once_exact_path() -> None:
    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/candidate/session/{token}/schedule"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(matches) == 1


@pytest.mark.asyncio
async def test_schedule_endpoint_persists_and_sends_emails(
    async_client, async_session, override_dependencies
):
    recruiter, simulation, cs = await _seed_claimed_session(async_session)
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
    assert recruiter.email in recipients
    assert any("Schedule confirmed" in message.subject for message in provider.sent)


@pytest.mark.asyncio
async def test_schedule_endpoint_idempotent_and_conflict(
    async_client, async_session, override_dependencies
):
    _recruiter, _simulation, cs = await _seed_claimed_session(async_session)
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


@pytest.mark.asyncio
async def test_schedule_endpoint_rejects_invalid_timezone_and_past(
    async_client, async_session, override_dependencies
):
    _recruiter, _simulation, cs = await _seed_claimed_session(async_session)
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


@pytest.mark.asyncio
async def test_schedule_endpoint_rejects_unclaimed_session(
    async_client, async_session, override_dependencies
):
    _recruiter, _simulation, cs = await _seed_claimed_session(async_session)

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


@pytest.mark.asyncio
async def test_schedule_endpoint_rejects_expired_token_with_error_code(
    async_client, async_session, override_dependencies
):
    _recruiter, _simulation, cs = await _seed_claimed_session(async_session)
    await _claim(async_client, cs.token, cs.invite_email)
    cs.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await async_session.commit()

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

    assert response.status_code == 410
    body = response.json()
    assert body["detail"] == "Invite token expired"
    assert body["errorCode"] == "INVITE_TOKEN_EXPIRED"
    assert len(provider.sent) == 0


@pytest.mark.asyncio
async def test_resolve_and_invites_include_schedule_fields(
    async_client, async_session, override_dependencies
):
    _recruiter, _simulation, cs = await _seed_claimed_session(async_session)
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
