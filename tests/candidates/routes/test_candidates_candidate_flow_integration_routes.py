from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    serialize_day_windows,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
)
from app.shared.jobs import worker
from tests.shared.factories import create_talent_partner


def _task_id_by_day(sim_payload: dict, day_index: int) -> int:
    task = next(
        (item for item in sim_payload["tasks"] if item["day_index"] == day_index), None
    )
    if task is None:
        raise AssertionError(f"Task with day_index={day_index} missing from payload")
    return task["id"]


async def _unlock_schedule(async_session, *, candidate_session_id: int) -> None:
    candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == candidate_session_id)
        )
    ).scalar_one()
    _trial = (
        await async_session.execute(
            select(Trial).where(Trial.id == candidate_session.trial_id)
        )
    ).scalar_one()
    now_utc = datetime.now(UTC).replace(microsecond=0)
    open_window_start = now_utc - timedelta(days=1)
    open_window_end = now_utc + timedelta(days=1)
    scheduled_start = open_window_start
    day_windows = [
        {
            "dayIndex": day_index,
            "windowStartAt": open_window_start,
            "windowEndAt": open_window_end,
        }
        for day_index in range(1, 6)
    ]
    candidate_session.scheduled_start_at = scheduled_start
    candidate_session.candidate_timezone = "America/New_York"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()


@pytest.mark.asyncio
async def test_full_flow_invite_through_first_submission(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    talent_partner = await create_talent_partner(async_session, email="flow@test.com")

    sim_payload = {
        "title": "Flow Test Sim",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "End-to-end candidate flow",
    }
    sim_res = await async_client.post(
        "/api/trials", json=sim_payload, headers=auth_header_factory(talent_partner)
    )
    assert sim_res.status_code == 201, sim_res.text
    sim_body = sim_res.json()
    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="candidate-flow-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    activate_res = await async_client.post(
        f"/api/trials/{sim_body['id']}/activate",
        json={"confirm": True},
        headers=auth_header_factory(talent_partner),
    )
    assert activate_res.status_code == 200, activate_res.text

    invite_res = await async_client.post(
        f"/api/trials/{sim_body['id']}/invite",
        headers=auth_header_factory(talent_partner),
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
