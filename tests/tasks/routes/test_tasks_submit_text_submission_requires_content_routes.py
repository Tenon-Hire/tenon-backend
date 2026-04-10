from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_text_submission_requires_content(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

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

    current = await get_current_task(async_client, cs_id, access_token)
    task_id = current["currentTask"]["id"]

    res = await async_client.post(
        f"/api/tasks/{task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={"contentText": "   "},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "contentText is required"
