from __future__ import annotations

import pytest

from app.shared.database.shared_database_models_model import TaskDraft
from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_submit_day1_text_creates_submission_and_advances(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

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

    current = await get_current_task(async_client, cs_id, access_token)
    assert current["currentDayIndex"] == 1
    day1_task_id = current["currentTask"]["id"]
    draft = await async_client.put(
        f"/api/tasks/{day1_task_id}/draft",
        headers=candidate_headers(cs_id, access_token),
        json={"contentText": "Draft before submit"},
    )
    assert draft.status_code == 200, draft.text

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
    saved_draft = (
        await async_session.execute(
            select(TaskDraft).where(
                TaskDraft.candidate_session_id == cs_id,
                TaskDraft.task_id == day1_task_id,
            )
        )
    ).scalar_one()
    assert saved_draft.finalized_submission_id == body["submissionId"]
    assert saved_draft.finalized_at is not None

    current2 = await get_current_task(async_client, cs_id, access_token)
    assert current2["currentDayIndex"] == 2
