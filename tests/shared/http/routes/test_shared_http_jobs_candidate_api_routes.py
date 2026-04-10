from __future__ import annotations

import pytest

from app.shared.database.shared_database_models_model import Company
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_SUCCEEDED,
)
from tests.shared.factories import (
    create_candidate_session,
    create_job,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_get_job_status_candidate_ownership(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-candidate-owner@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session, trial=sim, invite_email="candidate-owner@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_SUCCEEDED,
        job_type="transcript_processing",
        payload_json={"candidateSessionId": cs.id},
        result_json={"summary": "done"},
        candidate_session=cs,
    )
    await async_session.commit()

    ok = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["status"] == "completed"
    assert body["pollAfterMs"] == 0
    assert body["result"] == {"summary": "done"}

    denied = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": "Bearer candidate:not-owner@test.com"},
    )
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_get_job_status_candidate_sub_mismatch_returns_404(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-candidate-sub-owner@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="candidate-sub-owner@test.com",
        candidate_auth0_sub="candidate-someone-else@test.com",
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_SUCCEEDED,
        job_type="transcript_processing",
        payload_json={"candidateSessionId": cs.id},
        candidate_session=cs,
    )
    await async_session.commit()

    denied = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert denied.status_code == 404
    body = denied.json()
    assert body["errorCode"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_job_status_candidate_cannot_read_company_scoped_job(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-candidate-company-scope@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session, trial=sim, invite_email="candidate-company-scope@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_SUCCEEDED,
        job_type="scenario_generation",
        payload_json={"trialId": sim.id},
        result_json={"ok": True},
        candidate_session=None,
    )
    await async_session.commit()

    denied = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert denied.status_code == 404
    body = denied.json()
    assert body["errorCode"] == "JOB_NOT_FOUND"
    assert body["retryable"] is False
