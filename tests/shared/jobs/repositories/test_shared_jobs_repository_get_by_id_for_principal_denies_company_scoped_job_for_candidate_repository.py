from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_get_by_id_for_principal_denies_company_scoped_job_for_candidate(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-owner-company-scoped@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="jobs-candidate-company-scoped@test.com",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-company-scoped",
        payload_json={"trialId": sim.id},
        company_id=talent_partner.company_id,
        candidate_session_id=None,
    )

    candidate_principal = _principal(
        cs.invite_email,
        ["candidate:access"],
        sub="candidate-company-scoped",
        email_verified=True,
    )
    denied = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, candidate_principal
    )
    assert denied is None
