from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_out_of_order_submission_rejected_400(
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

    # Candidate is on day 1, but tries to submit day 3
    day3_task_id = task_id_by_day(sim, 3)

    r = await async_client.post(
        f"/api/tasks/{day3_task_id}/submit",
        headers=candidate_headers(cs_id, access_token),
        json={},
    )
    assert r.status_code == 400, r.text
