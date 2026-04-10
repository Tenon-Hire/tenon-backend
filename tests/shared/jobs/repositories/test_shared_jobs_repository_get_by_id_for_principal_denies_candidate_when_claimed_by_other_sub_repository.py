from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_get_by_id_for_principal_denies_candidate_when_claimed_by_other_sub(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-owner-sub-check@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="jobs-candidate-sub-check@test.com",
        candidate_auth0_sub="candidate-sub-owner",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-sub-check",
        payload_json={"candidateSessionId": cs.id},
        company_id=talent_partner.company_id,
        candidate_session_id=cs.id,
    )

    wrong_sub_principal = _principal(
        cs.invite_email,
        ["candidate:access"],
        sub="candidate-sub-attacker",
        email_verified=True,
    )
    denied = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, wrong_sub_principal
    )
    assert denied is None
