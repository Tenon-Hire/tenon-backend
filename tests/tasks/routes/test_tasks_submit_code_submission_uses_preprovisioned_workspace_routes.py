from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_code_submission_uses_preprovisioned_workspace(
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

    # Complete day 1 (text) to advance to day 2 (code)
    day1 = await get_current_task(async_client, cs_id, access_token)
    day1_task_id = day1["currentTask"]["id"]
    ok = await async_client.post(
        f"/api/tasks/{day1_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={"contentText": "design answer"},
    )
    assert ok.status_code == 201, ok.text

    day2 = await get_current_task(async_client, cs_id, access_token)
    assert day2["currentDayIndex"] == 2
    day2_task_id = day2["currentTask"]["id"]

    workspace = (
        await async_session.execute(
            select(Workspace).where(
                Workspace.candidate_session_id == cs_id,
                Workspace.task_id == day2_task_id,
            )
        )
    ).scalar_one_or_none()
    assert workspace is not None

    res = await async_client.post(
        f"/api/tasks/{day2_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={},
    )
    assert res.status_code == 201, res.text
