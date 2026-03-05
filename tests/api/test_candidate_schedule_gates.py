from __future__ import annotations

import json
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.scheduling.day_windows import (
    derive_day_windows,
    serialize_day_windows,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _local_window_start_utc(timezone_name: str, *, days_ahead: int) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=days_ahead)
    local_start = datetime.combine(local_date, time(hour=9, minute=0), tzinfo=zone)
    return local_start.astimezone(UTC).replace(microsecond=0)


async def _set_schedule(
    *,
    async_session,
    candidate_session,
    scheduled_start_at: datetime,
    timezone_name: str,
) -> None:
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start_at,
        candidate_tz=timezone_name,
        day_window_start_local=candidate_session.simulation.day_window_start_local,
        day_window_end_local=candidate_session.simulation.day_window_end_local,
        overrides=candidate_session.simulation.day_window_overrides_json,
        overrides_enabled=bool(
            candidate_session.simulation.day_window_overrides_enabled
        ),
        total_days=5,
    )
    candidate_session.scheduled_start_at = scheduled_start_at
    candidate_session.candidate_timezone = timezone_name
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()


@pytest.mark.asyncio
async def test_codespace_status_pre_start_returns_schedule_not_started(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="status-prestart@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        with_default_schedule=False,
    )
    scheduled_start = _local_window_start_utc("America/New_York", days_ahead=2)
    await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=scheduled_start,
        timezone_name="America/New_York",
    )

    response = await async_client.get(
        f"/api/tasks/{tasks[0].id}/codespace/status",
        headers=candidate_header_factory(candidate_session),
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["detail"] == "Simulation has not started yet."
    assert body["errorCode"] == "SCHEDULE_NOT_STARTED"
    assert body["retryable"] is True
    assert body["details"]["startAt"] == scheduled_start.isoformat().replace(
        "+00:00", "Z"
    )
    assert body["details"]["windowStartAt"] == scheduled_start.isoformat().replace(
        "+00:00", "Z"
    )
    assert body["details"]["windowEndAt"] is not None


@pytest.mark.asyncio
async def test_current_task_mismatch_still_ownership_error_before_schedule_gate(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="ownership-order@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="owner@example.com",
        with_default_schedule=False,
    )
    await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=2),
        timezone_name="America/New_York",
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:attacker@example.com",
            "x-candidate-session-id": str(candidate_session.id),
        },
    )
    assert response.status_code == 403, response.text
    assert response.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"


@pytest.mark.asyncio
async def test_resolve_pre_start_returns_locked_payload_without_content_leaks(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="resolve-prestart@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="locked@example.com",
        with_default_schedule=False,
    )
    scheduled_start = _local_window_start_utc("America/New_York", days_ahead=2)
    await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=scheduled_start,
        timezone_name="America/New_York",
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.token}",
        headers={"Authorization": "Bearer candidate:locked@example.com"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["candidateSessionId"] == candidate_session.id
    assert body["startAt"] == scheduled_start.isoformat().replace("+00:00", "Z")
    assert body["windowStartAt"] == scheduled_start.isoformat().replace("+00:00", "Z")
    assert body["windowEndAt"] is not None
    assert body["candidateTimezone"] == "America/New_York"
    assert body["simulation"]["id"] == sim.id

    for key in (
        "storyline",
        "prestart",
        "currentTask",
        "tasks",
        "repoUrl",
        "codespaceUrl",
        "templateRepoFullName",
        "resources",
    ):
        assert key not in body

    payload_blob = json.dumps(body).lower()
    assert "github.com" not in payload_blob
    assert "codespace" not in payload_blob
