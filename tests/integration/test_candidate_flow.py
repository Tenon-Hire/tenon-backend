from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.domains import CandidateSession, Simulation
from app.services.scheduling.day_windows import (
    derive_day_windows,
    serialize_day_windows,
)
from tests.factories import create_recruiter


def _task_id_by_day(sim_payload: dict, day_index: int) -> int:
    for task in sim_payload["tasks"]:
        if task["day_index"] == day_index:
            return task["id"]
    raise AssertionError(f"Task with day_index={day_index} missing from payload")


def _local_window_start_utc(timezone_name: str, *, days_ahead: int) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=days_ahead)
    local_start = datetime.combine(local_date, time(hour=9, minute=0), tzinfo=zone)
    return local_start.astimezone(UTC).replace(microsecond=0)


async def _unlock_schedule(async_session, *, candidate_session_id: int) -> None:
    candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == candidate_session_id)
        )
    ).scalar_one()
    simulation = (
        await async_session.execute(
            select(Simulation).where(Simulation.id == candidate_session.simulation_id)
        )
    ).scalar_one()
    scheduled_start = _local_window_start_utc("America/New_York", days_ahead=-1)
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start,
        candidate_tz="America/New_York",
        day_window_start_local=simulation.day_window_start_local,
        day_window_end_local=simulation.day_window_end_local,
        overrides=simulation.day_window_overrides_json,
        overrides_enabled=bool(simulation.day_window_overrides_enabled),
        total_days=5,
    )
    candidate_session.scheduled_start_at = scheduled_start
    candidate_session.candidate_timezone = "America/New_York"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()


@pytest.mark.asyncio
async def test_full_flow_invite_through_first_submission(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    recruiter = await create_recruiter(async_session, email="flow@test.com")

    sim_payload = {
        "title": "Flow Test Sim",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "End-to-end candidate flow",
    }
    sim_res = await async_client.post(
        "/api/simulations", json=sim_payload, headers=auth_header_factory(recruiter)
    )
    assert sim_res.status_code == 201, sim_res.text
    sim_body = sim_res.json()
    activate_res = await async_client.post(
        f"/api/simulations/{sim_body['id']}/activate",
        json={"confirm": True},
        headers=auth_header_factory(recruiter),
    )
    assert activate_res.status_code == 200, activate_res.text

    invite_res = await async_client.post(
        f"/api/simulations/{sim_body['id']}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Flow Candidate", "inviteEmail": "flow@example.com"},
    )
    assert invite_res.status_code == 200, invite_res.text
    invite = invite_res.json()

    cs_id = invite["candidateSessionId"]
    access_token = "candidate:flow@example.com"

    claim_res = await async_client.get(
        f"/api/candidate/session/{invite['token']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert claim_res.status_code == 200, claim_res.text
    await _unlock_schedule(async_session, candidate_session_id=cs_id)

    current_res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {access_token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert current_res.status_code == 200, current_res.text
    assert current_res.json()["currentDayIndex"] == 1

    day1_task_id = _task_id_by_day(sim_body, 1)
    submit_res = await async_client.post(
        f"/api/tasks/{day1_task_id}/submit",
        headers={
            "Authorization": f"Bearer {access_token}",
            "x-candidate-session-id": str(cs_id),
        },
        json={"contentText": "Day 1 answer"},
    )
    assert submit_res.status_code == 201, submit_res.text
    submit_body = submit_res.json()
    assert submit_body["progress"]["completed"] == 1
    assert submit_body["isComplete"] is False
