from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_submit_day3_debug_returns_and_persists_final_sha(
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

    day1_task_id = (await get_current_task(async_client, cs_id, access_token))[
        "currentTask"
    ]["id"]
    day1 = await async_client.post(
        f"/api/tasks/{day1_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={"contentText": "done"},
    )
    assert day1.status_code == 201, day1.text

    day2_task_id = (await get_current_task(async_client, cs_id, access_token))[
        "currentTask"
    ]["id"]
    day2_init = await async_client.post(
        f"/api/tasks/{day2_task_id}/codespace/init",
        headers=candidate_headers(cs_id, access_token),
        json={"githubUsername": "octocat"},
    )
    assert day2_init.status_code == 200, day2_init.text
    day2_submit = await async_client.post(
        f"/api/tasks/{day2_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={},
    )
    assert day2_submit.status_code == 201, day2_submit.text
    day2_repo = day2_init.json()["repoFullName"]

    current3 = await get_current_task(async_client, cs_id, access_token)
    assert current3["currentDayIndex"] == 3
    day3_task_id = current3["currentTask"]["id"]

    day3_init = await async_client.post(
        f"/api/tasks/{day3_task_id}/codespace/init",
        headers=candidate_headers(cs_id, access_token),
        json={"githubUsername": "octocat"},
    )
    assert day3_init.status_code == 200, day3_init.text
    assert day3_init.json()["repoFullName"] == day2_repo

    day3_submit = await async_client.post(
        f"/api/tasks/{day3_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={},
    )
    assert day3_submit.status_code == 201, day3_submit.text
    day3_body = day3_submit.json()
    assert day3_body["commitSha"] is not None
    assert day3_body["finalSha"] == day3_body["commitSha"]
    assert day3_body["checkpointSha"] is None

    stmt = select(Submission).where(
        Submission.candidate_session_id == cs_id,
        Submission.task_id.in_([day2_task_id, day3_task_id]),
    )
    submissions = (await async_session.execute(stmt)).scalars().all()
    assert len(submissions) == 2
    by_task_id = {sub.task_id: sub for sub in submissions}
    assert by_task_id[day2_task_id].code_repo_path == day2_repo
    assert by_task_id[day3_task_id].code_repo_path == day2_repo
    assert (
        by_task_id[day2_task_id].checkpoint_sha == by_task_id[day2_task_id].commit_sha
    )
    assert by_task_id[day2_task_id].final_sha is None
    assert by_task_id[day3_task_id].final_sha == by_task_id[day3_task_id].commit_sha
    assert by_task_id[day3_task_id].checkpoint_sha is None
