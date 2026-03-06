from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.domains import CandidateSession, Simulation
from app.services.scheduling.day_windows import serialize_day_windows
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _build_closed_day_windows(*, now_utc: datetime) -> list[dict[str, datetime | int]]:
    day_windows: list[dict[str, datetime | int]] = []
    for day_index in range(1, 6):
        window_start = now_utc + timedelta(days=day_index)
        window_end = window_start + timedelta(hours=8)
        day_windows.append(
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
        )
    return day_windows


async def _set_closed_schedule(async_session, *, candidate_session_id: int) -> None:
    candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == candidate_session_id)
        )
    ).scalar_one()
    _simulation = (
        await async_session.execute(
            select(Simulation).where(Simulation.id == candidate_session.simulation_id)
        )
    ).scalar_one()

    now_utc = datetime.now(UTC).replace(microsecond=0)
    day_windows = _build_closed_day_windows(now_utc=now_utc)
    candidate_session.scheduled_start_at = day_windows[0]["windowStartAt"]
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()


@pytest.mark.asyncio
async def test_put_then_get_task_draft_round_trips(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(async_session, email="draft-put-get@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    day1_task = tasks[0]
    headers = candidate_header_factory(candidate_session)
    payload = {
        "contentText": "## Plan\n- step 1",
        "contentJson": {
            "reflection": {
                "challenges": "api design",
                "decisions": "favor idempotency",
            }
        },
    }

    put_response = await async_client.put(
        f"/api/tasks/{day1_task.id}/draft",
        headers=headers,
        json=payload,
    )
    assert put_response.status_code == 200, put_response.text
    put_body = put_response.json()
    assert put_body["taskId"] == day1_task.id
    assert put_body["updatedAt"] is not None

    get_response = await async_client.get(
        f"/api/tasks/{day1_task.id}/draft",
        headers=headers,
    )
    assert get_response.status_code == 200, get_response.text
    get_body = get_response.json()
    assert get_body["taskId"] == day1_task.id
    assert get_body["contentText"] == payload["contentText"]
    assert get_body["contentJson"] == payload["contentJson"]
    assert get_body["updatedAt"] == put_body["updatedAt"]
    assert get_body["finalizedAt"] is None
    assert get_body["finalizedSubmissionId"] is None


@pytest.mark.asyncio
async def test_get_task_draft_missing_returns_not_found(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(async_session, email="draft-missing@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
    )
    assert response.status_code == 404, response.text
    assert response.json()["errorCode"] == "DRAFT_NOT_FOUND"


@pytest.mark.asyncio
async def test_put_task_draft_outside_window_returns_task_window_closed(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(async_session, email="draft-window@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=False,
    )
    await async_session.commit()

    await _set_closed_schedule(async_session, candidate_session_id=candidate_session.id)

    response = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
        json={"contentText": "not now"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"


@pytest.mark.asyncio
async def test_put_task_draft_after_submission_returns_draft_finalized(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(async_session, email="draft-finalized@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    headers = candidate_header_factory(candidate_session)
    put_first = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=headers,
        json={"contentText": "before submit"},
    )
    assert put_first.status_code == 200, put_first.text

    submit_response = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=headers,
        json={"contentText": "manual submit wins"},
    )
    assert submit_response.status_code == 201, submit_response.text

    put_second = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=headers,
        json={"contentText": "should fail"},
    )
    assert put_second.status_code == 409, put_second.text
    assert put_second.json()["errorCode"] == "DRAFT_FINALIZED"


@pytest.mark.asyncio
async def test_put_task_draft_rejects_oversized_content_text(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(async_session, email="draft-size-text@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    oversized_text = "x" * (200 * 1024 + 1)
    response = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
        json={"contentText": oversized_text},
    )
    assert response.status_code == 413, response.text
    body = response.json()
    assert body["errorCode"] == "DRAFT_CONTENT_TOO_LARGE"
    assert body["details"]["field"] == "contentText"


@pytest.mark.asyncio
async def test_put_task_draft_rejects_oversized_content_json(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(async_session, email="draft-size-json@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    oversized_json = {"blob": "y" * (200 * 1024 + 128)}
    response = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
        json={"contentJson": oversized_json},
    )
    assert response.status_code == 413, response.text
    body = response.json()
    assert body["errorCode"] == "DRAFT_CONTENT_TOO_LARGE"
    assert body["details"]["field"] == "contentJson"
