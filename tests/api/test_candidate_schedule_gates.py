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
) -> list[dict[str, object]]:
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
    return day_windows


def _window_by_day(
    day_windows: list[dict[str, object]],
    *,
    day_index: int,
) -> dict[str, object]:
    for window in day_windows:
        if int(window["dayIndex"]) == day_index:
            return window
    raise AssertionError(f"Missing day window for day_index={day_index}")


def _window_iso(window: dict[str, object], key: str) -> str:
    value = window[key]
    assert isinstance(value, datetime)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_codespace_status_pre_start_returns_task_window_closed(
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
    day_windows = await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=scheduled_start,
        timezone_name="America/New_York",
    )
    day1_window = _window_by_day(day_windows, day_index=1)

    response = await async_client.get(
        f"/api/tasks/{tasks[0].id}/codespace/status",
        headers=candidate_header_factory(candidate_session),
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["detail"] == "Task is closed outside the scheduled window."
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert body["retryable"] is True
    assert body["details"]["windowStartAt"] == _window_iso(day1_window, "windowStartAt")
    assert body["details"]["windowEndAt"] == _window_iso(day1_window, "windowEndAt")
    assert body["details"]["nextOpenAt"] == _window_iso(day1_window, "windowStartAt")


@pytest.mark.asyncio
async def test_codespace_init_pre_start_returns_task_window_closed(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="init-prestart@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        with_default_schedule=False,
    )
    day_windows = await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=2),
        timezone_name="America/New_York",
    )
    day2_window = _window_by_day(day_windows, day_index=2)

    response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=candidate_header_factory(candidate_session),
        json={"githubUsername": "octocat"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert body["details"]["windowStartAt"] == _window_iso(day2_window, "windowStartAt")
    assert body["details"]["windowEndAt"] == _window_iso(day2_window, "windowEndAt")
    assert body["details"]["nextOpenAt"] == _window_iso(day2_window, "windowStartAt")


@pytest.mark.asyncio
async def test_run_pre_start_returns_task_window_closed(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="run-prestart@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        with_default_schedule=False,
    )
    day_windows = await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=2),
        timezone_name="America/New_York",
    )
    day2_window = _window_by_day(day_windows, day_index=2)

    response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/run",
        headers=candidate_header_factory(candidate_session),
        json={},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert body["details"]["windowStartAt"] == _window_iso(day2_window, "windowStartAt")
    assert body["details"]["windowEndAt"] == _window_iso(day2_window, "windowEndAt")
    assert body["details"]["nextOpenAt"] == _window_iso(day2_window, "windowStartAt")


@pytest.mark.asyncio
async def test_submit_pre_start_returns_task_window_closed(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="submit-prestart@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        with_default_schedule=False,
    )
    day_windows = await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=2),
        timezone_name="America/New_York",
    )
    day1_window = _window_by_day(day_windows, day_index=1)

    response = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=candidate_header_factory(candidate_session),
        json={"contentText": "not yet"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert body["details"]["windowStartAt"] == _window_iso(day1_window, "windowStartAt")
    assert body["details"]["windowEndAt"] == _window_iso(day1_window, "windowEndAt")
    assert body["details"]["nextOpenAt"] == _window_iso(day1_window, "windowStartAt")


@pytest.mark.asyncio
async def test_run_and_submit_post_cutoff_return_task_window_closed(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="post-cutoff@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        with_default_schedule=False,
    )
    now_utc = datetime.now(UTC).replace(microsecond=0)
    day_windows = []
    for day_index in range(1, 6):
        window_end = now_utc - timedelta(days=6 - day_index)
        window_start = window_end - timedelta(hours=8)
        day_windows.append(
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
        )
    candidate_session.scheduled_start_at = day_windows[0]["windowStartAt"]
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()
    day2_window = _window_by_day(day_windows, day_index=2)

    run_response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/run",
        headers=candidate_header_factory(candidate_session),
        json={},
    )
    assert run_response.status_code == 409, run_response.text
    run_body = run_response.json()
    assert run_body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert run_body["details"]["windowStartAt"] == _window_iso(
        day2_window, "windowStartAt"
    )
    assert run_body["details"]["windowEndAt"] == _window_iso(day2_window, "windowEndAt")

    submit_response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/submit",
        headers=candidate_header_factory(candidate_session),
        json={},
    )
    assert submit_response.status_code == 409, submit_response.text
    submit_body = submit_response.json()
    assert submit_body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert submit_body["details"]["windowStartAt"] == _window_iso(
        day2_window, "windowStartAt"
    )
    assert submit_body["details"]["windowEndAt"] == _window_iso(
        day2_window, "windowEndAt"
    )


@pytest.mark.asyncio
async def test_submit_invalid_schedule_returns_schedule_invalid_window(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="submit-invalid-window@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        with_default_schedule=False,
    )
    candidate_session.scheduled_start_at = datetime.now(UTC) - timedelta(days=1)
    candidate_session.candidate_timezone = "Invalid/Timezone"
    candidate_session.day_windows_json = None
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=candidate_header_factory(candidate_session),
        json={"contentText": "still blocked"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["detail"] == "Schedule window configuration is invalid."
    assert body["errorCode"] == "SCHEDULE_INVALID_WINDOW"
    assert body["retryable"] is False
    assert body["details"] == {
        "candidateSessionId": candidate_session.id,
        "taskId": tasks[0].id,
        "dayIndex": tasks[0].day_index,
        "windowStartAt": None,
        "windowEndAt": None,
    }


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
async def test_current_task_requires_candidate_session_header(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="header-required@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="header-required-owner@example.com",
        with_default_schedule=False,
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:header-required-owner@example.com",
        },
    )
    assert response.status_code == 401, response.text
    assert response.json()["errorCode"] == "CANDIDATE_SESSION_HEADER_REQUIRED"


@pytest.mark.asyncio
async def test_current_task_rejects_non_integer_session_header(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="header-nonint@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="header-nonint-owner@example.com",
        with_default_schedule=False,
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:header-nonint-owner@example.com",
            "x-candidate-session-id": "not-an-int",
        },
    )
    assert response.status_code == 401, response.text
    assert response.json()["errorCode"] == "CANDIDATE_SESSION_HEADER_REQUIRED"


@pytest.mark.asyncio
async def test_current_task_rejects_non_positive_session_header(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="header-zero@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="header-zero-owner@example.com",
        with_default_schedule=False,
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:header-zero-owner@example.com",
            "x-candidate-session-id": "0",
        },
    )
    assert response.status_code == 401, response.text
    assert response.json()["errorCode"] == "CANDIDATE_SESSION_HEADER_REQUIRED"


@pytest.mark.asyncio
async def test_current_task_rejects_mismatched_session_header_without_schedule_leak(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="header-mismatch@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="owner2@example.com",
        with_default_schedule=False,
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:owner2@example.com",
            "x-candidate-session-id": str(candidate_session.id + 1000),
        },
    )
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["errorCode"] == "CANDIDATE_SESSION_HEADER_MISMATCH"
    assert body["details"] == {}


@pytest.mark.asyncio
async def test_current_task_includes_current_window_metadata(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="current-window@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="window-owner@example.com",
        with_default_schedule=False,
    )
    await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=-1),
        timezone_name="America/New_York",
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:window-owner@example.com",
            "x-candidate-session-id": str(candidate_session.id),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    current_window = body["currentWindow"]
    assert current_window is not None
    assert current_window["windowStartAt"] is not None
    assert current_window["windowEndAt"] is not None
    assert isinstance(current_window["isOpen"], bool)
    assert current_window["now"] is not None


@pytest.mark.asyncio
async def test_current_task_omits_current_window_when_bounds_are_invalid(
    async_client, async_session
):
    recruiter = await create_recruiter(
        async_session, email="current-window-invalid@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="window-invalid-owner@example.com",
        with_default_schedule=False,
    )
    candidate_session.scheduled_start_at = datetime.now(UTC) - timedelta(days=1)
    candidate_session.candidate_timezone = "Invalid/Timezone"
    candidate_session.day_windows_json = None
    await async_session.commit()

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:window-invalid-owner@example.com",
            "x-candidate-session-id": str(candidate_session.id),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["currentWindow"] is None


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
