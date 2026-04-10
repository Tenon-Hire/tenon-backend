from __future__ import annotations

import pytest

from app.shared.jobs.repositories import repository as jobs_repo
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_get_job_status_hidden_for_wrong_talent_partner(
    async_client, async_session
):
    owner = await create_talent_partner(async_session, email="jobs-owner@test.com")
    other = await create_talent_partner(async_session, email="jobs-other@test.com")
    sim, _ = await create_trial(async_session, created_by=owner)
    cs = await create_candidate_session(async_session, trial=sim)
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="scenario-owner-2",
        payload_json={"trialId": sim.id},
        company_id=owner.company_id,
        candidate_session_id=cs.id,
    )
    res = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer talent_partner:{other.email}"},
    )
    assert res.status_code == 404
    body = res.json()
    assert body["errorCode"] == "JOB_NOT_FOUND"
    assert body["retryable"] is False
