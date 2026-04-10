from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_submit_day2_code_records_actions_run(
    async_client, async_session: AsyncSession, monkeypatch, actions_stubber
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    actions_stubber()

    talent_partner_email = "talent_partnerA@winoe.com"
    await seed_talent_partner(
        async_session, email=talent_partner_email, company_name="TalentPartner A"
    )

    sim = await create_trial(async_client, async_session, talent_partner_email)
    sim_id = sim["id"]

    invite = await invite_candidate(async_client, sim_id, talent_partner_email)
    await claim_session(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    await unlock_schedule(async_session, candidate_session_id=cs_id)
    access_token = "candidate:jane@example.com"

    # Submit Day 1 (text)
    day1_task_id = (await get_current_task(async_client, cs_id, access_token))[
        "currentTask"
    ]["id"]
    r1 = await async_client.post(
        f"/api/tasks/{day1_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={"contentText": "done"},
    )
    assert r1.status_code == 201, r1.text

    # Submit Day 2 (code)
    current2 = await get_current_task(async_client, cs_id, access_token)
    assert current2["currentDayIndex"] == 2
    day2_task_id = current2["currentTask"]["id"]

    # Init workspace then submit (no code payload)
    init_resp = await async_client.post(
        f"/api/tasks/{day2_task_id}/codespace/init",
        headers=candidate_headers(cs_id, access_token),
        json={"githubUsername": "octocat"},
    )
    assert init_resp.status_code == 200, init_resp.text

    r2 = await async_client.post(
        f"/api/tasks/{day2_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={},
    )
    assert r2.status_code == 201, r2.text
    day2_body = r2.json()
    assert day2_body["commitSha"] is not None
    assert day2_body["checkpointSha"] == day2_body["commitSha"]
    assert day2_body["finalSha"] is None

    # Verify persisted
    stmt = select(Submission).where(
        Submission.candidate_session_id == cs_id,
        Submission.task_id == day2_task_id,
    )
    sub = (await async_session.execute(stmt)).scalar_one()
    assert sub.commit_sha is not None
    assert sub.checkpoint_sha == sub.commit_sha
    assert sub.final_sha is None
    assert sub.workflow_run_id is not None
    assert sub.code_repo_path is not None
