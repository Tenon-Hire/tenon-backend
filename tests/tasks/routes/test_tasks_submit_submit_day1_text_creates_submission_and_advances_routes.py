from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_submit_day1_text_creates_submission_and_advances(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

    recruiter_email = "recruiterA@tenon.com"
    await seed_recruiter(
        async_session, email=recruiter_email, company_name="Recruiter A"
    )

    sim = await create_simulation(async_client, async_session, recruiter_email)
    sim_id = sim["id"]

    invite = await invite_candidate(async_client, sim_id, recruiter_email)
    await claim_session(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    await unlock_schedule(async_session, candidate_session_id=cs_id)
    access_token = "candidate:jane@example.com"

    current = await get_current_task(async_client, cs_id, access_token)
    assert current["currentDayIndex"] == 1
    day1_task_id = current["currentTask"]["id"]

    submit = await async_client.post(
        f"/api/tasks/{day1_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={"contentText": "Day 1 design answer"},
    )
    assert submit.status_code == 201, submit.text
    body = submit.json()
    assert body["candidateSessionId"] == cs_id
    assert body["taskId"] == day1_task_id
    assert body["progress"]["completed"] == 1

    current2 = await get_current_task(async_client, cs_id, access_token)
    assert current2["currentDayIndex"] == 2
