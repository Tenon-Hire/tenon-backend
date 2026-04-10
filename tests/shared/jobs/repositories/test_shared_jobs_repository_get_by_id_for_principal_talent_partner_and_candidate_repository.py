from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_get_by_id_for_principal_talent_partner_and_candidate(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-owner-lookup@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="jobs-candidate-lookup@test.com",
        candidate_auth0_sub="candidate-sub-1",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-principal",
        payload_json={"candidateSessionId": cs.id},
        company_id=talent_partner.company_id,
        candidate_session_id=cs.id,
    )

    talent_partner_principal = _principal(
        talent_partner.email, ["talent_partner:access"]
    )
    candidate_principal = _principal(
        "jobs-candidate-lookup@test.com",
        ["candidate:access"],
        sub="candidate-sub-1",
        email_verified=True,
    )
    unknown_principal = _principal(
        "nobody@test.com",
        ["candidate:access"],
        email_verified=True,
    )

    talent_partner_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, talent_partner_principal
    )
    candidate_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, candidate_principal
    )
    denied_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, unknown_principal
    )
    assert talent_partner_view is not None
    assert candidate_view is not None
    assert denied_view is None


@pytest.mark.asyncio
async def test_get_by_id_for_principal_talent_partner_without_company_id_is_denied(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="jobs-owner-no-company@test.com"
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-no-company",
        payload_json={"x": 1},
        company_id=talent_partner.company_id,
    )
    talent_partner.company_id = None
    await async_session.commit()

    talent_partner_principal = _principal(
        talent_partner.email, ["talent_partner:access"]
    )
    talent_partner_view = await jobs_repo.get_by_id_for_principal(
        async_session,
        job.id,
        talent_partner_principal,
    )

    assert talent_partner_view is None
