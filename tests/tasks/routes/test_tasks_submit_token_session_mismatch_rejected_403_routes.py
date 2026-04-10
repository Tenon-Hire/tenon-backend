from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_token_session_mismatch_rejected_403(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

    talent_partner_email = "talent_partnerA@winoe.com"
    await seed_talent_partner(
        async_session, email=talent_partner_email, company_name="TalentPartner A"
    )

    sim = await create_trial(async_client, async_session, talent_partner_email)

    email_a = "jane@example.com"
    invite_a = await invite_candidate(
        async_client, sim["id"], talent_partner_email, invite_email=email_a
    )
    await claim_session(async_client, invite_a["token"], email_a)
    cs_id_a = invite_a["candidateSessionId"]
    await unlock_schedule(async_session, candidate_session_id=cs_id_a)
    token_a = f"candidate:{email_a}"

    email_b = "other@example.com"
    invite_b = await invite_candidate(
        async_client, sim["id"], talent_partner_email, invite_email=email_b
    )
    await claim_session(async_client, invite_b["token"], email_b)
    cs_id_b = invite_b["candidateSessionId"]
    await unlock_schedule(async_session, candidate_session_id=cs_id_b)
    token_b = f"candidate:{email_b}"

    current_b = await get_current_task(async_client, cs_id_b, token_b)
    task_id_b = current_b["currentTask"]["id"]

    # email A + session B => rejected
    r = await async_client.post(
        f"/api/tasks/{task_id_b}/submit",
        headers=candidate_headers(cs_id_b, token_a),
        json={"contentText": "nope"},
    )
    assert r.status_code == 403, r.text
    assert r.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"

    # sanity: A can still submit its own task
    current_a = await get_current_task(async_client, cs_id_a, token_a)
    task_id_a = current_a["currentTask"]["id"]
    r_ok = await async_client.post(
        f"/api/tasks/{task_id_a}/submit",
        headers=candidate_headers(cs_id_a, token_a),
        json={"contentText": "ok"},
    )
    assert r_ok.status_code == 201, r_ok.text
