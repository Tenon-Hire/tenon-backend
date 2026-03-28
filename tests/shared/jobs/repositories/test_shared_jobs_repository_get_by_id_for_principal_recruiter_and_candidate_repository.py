from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_get_by_id_for_principal_recruiter_and_candidate(async_session):
    recruiter = await create_recruiter(
        async_session, email="jobs-owner-lookup@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="jobs-candidate-lookup@test.com",
        candidate_auth0_sub="candidate-sub-1",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-principal",
        payload_json={"candidateSessionId": cs.id},
        company_id=recruiter.company_id,
        candidate_session_id=cs.id,
    )

    recruiter_principal = _principal(recruiter.email, ["recruiter:access"])
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

    recruiter_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, recruiter_principal
    )
    candidate_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, candidate_principal
    )
    denied_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, unknown_principal
    )
    assert recruiter_view is not None
    assert candidate_view is not None
    assert denied_view is None


@pytest.mark.asyncio
async def test_get_by_id_for_principal_recruiter_without_company_id_is_denied(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="jobs-owner-no-company@test.com"
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-no-company",
        payload_json={"x": 1},
        company_id=recruiter.company_id,
    )
    recruiter.company_id = None
    await async_session.commit()

    recruiter_principal = _principal(recruiter.email, ["recruiter:access"])
    recruiter_view = await jobs_repo.get_by_id_for_principal(
        async_session,
        job.id,
        recruiter_principal,
    )

    assert recruiter_view is None
