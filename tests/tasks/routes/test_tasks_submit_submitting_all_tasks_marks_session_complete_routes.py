from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_submitting_all_tasks_marks_session_complete(
    async_client, async_session: AsyncSession, monkeypatch, actions_stubber
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    actions_stubber()

    talent_partner_email = "talent_partnerA@winoe.com"
    await seed_talent_partner(
        async_session, email=talent_partner_email, company_name="TalentPartner A"
    )

    sim = await create_trial(async_client, async_session, talent_partner_email)
    invite = await invite_candidate(async_client, sim["id"], talent_partner_email)
    await claim_session(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    await unlock_schedule(async_session, candidate_session_id=cs_id)
    access_token = "candidate:jane@example.com"

    payloads_by_day = {
        1: {"contentText": "day1 design"},
        2: {},
        3: {},
        4: {"contentText": "handoff notes"},
        5: build_day5_reflection_payload(),
    }

    last_response = None
    for day_index in range(1, 6):
        current = await get_current_task(async_client, cs_id, access_token)
        assert current["currentDayIndex"] == day_index
        task_id = current["currentTask"]["id"]

        if current["currentTask"]["type"] == "code":
            init_resp = await async_client.post(
                f"/api/tasks/{task_id}/codespace/init",
                headers=candidate_headers(cs_id, access_token),
                json={"githubUsername": "octocat"},
            )
            assert init_resp.status_code == 200, init_resp.text

        last_response = await async_client.post(
            f"/api/tasks/{task_id}/submit",
            headers=candidate_headers(cs_id, access_token),
            json=payloads_by_day[day_index],
        )
        assert last_response.status_code == 201, last_response.text

    assert last_response is not None
    body = last_response.json()
    assert body["isComplete"] is True
    assert body["progress"]["completed"] == 5
    assert body["progress"]["total"] == 5

    cs = (
        await async_session.execute(
            select(Submission.candidate_session_id, Submission.id)
        )
    ).scalars()
    assert len(list(cs)) == 5

    cs_row = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()
    assert cs_row.status == "completed"
    assert cs_row.completed_at is not None
