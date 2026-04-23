from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_get_by_id_for_principal_allows_unverified_candidate(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-owner-unverified@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="jobs-candidate-unverified@test.com",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-unverified",
        payload_json={"candidateSessionId": cs.id},
        company_id=talent_partner.company_id,
        candidate_session_id=cs.id,
    )

    unverified_principal = _principal(
        cs.invite_email,
        ["candidate:access"],
        sub="candidate-unverified",
        email_verified=False,
    )
    denied = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, unverified_principal
    )
    assert denied is not None
    assert denied.id == job.id
