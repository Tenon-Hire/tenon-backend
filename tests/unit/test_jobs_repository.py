from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.auth.principal import Principal
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import JOB_STATUS_RUNNING
from tests.factories import (
    create_candidate_session,
    create_company,
    create_job,
    create_recruiter,
    create_simulation,
)


def _principal(
    email: str, permissions: list[str], *, sub: str | None = None
) -> Principal:
    return Principal(
        sub=sub or f"principal-{email}",
        email=email,
        name=email.split("@")[0],
        roles=[],
        permissions=permissions,
        claims={},
    )


@pytest.mark.asyncio
async def test_create_or_get_idempotent_returns_existing(async_session):
    company = await create_company(async_session, name="Jobs Co")

    first = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-1",
        payload_json={"a": 1},
        company_id=company.id,
    )
    second = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-1",
        payload_json={"a": 2},
        company_id=company.id,
    )

    assert first.id == second.id
    fetched = await jobs_repo.get_by_id(async_session, first.id)
    assert fetched is not None
    assert fetched.id == first.id


@pytest.mark.asyncio
async def test_create_or_get_idempotent_validates_payload_and_inputs(async_session):
    company = await create_company(async_session, name="Jobs Co 2")
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type=" ",
            idempotency_key="idem-2",
            payload_json={"ok": True},
            company_id=company.id,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key=" ",
            payload_json={"ok": True},
            company_id=company.id,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key="idem-2",
            payload_json={"ok": True},
            company_id=company.id,
            max_attempts=0,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key="idem-3",
            payload_json={"blob": "x" * (jobs_repo.MAX_JOB_PAYLOAD_BYTES + 1)},
            company_id=company.id,
        )


@pytest.mark.asyncio
async def test_claim_next_runnable_reclaims_stale_running_job(async_session):
    company = await create_company(async_session, name="Jobs Co 3")
    stale_time = datetime.now(UTC) - timedelta(minutes=20)
    running_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        attempt=1,
        next_run_at=None,
    )
    running_job.locked_at = stale_time
    await async_session.commit()

    claimed = await jobs_repo.claim_next_runnable(
        async_session,
        worker_id="w1",
        now=datetime.now(UTC),
        lease_seconds=300,
    )
    assert claimed is not None
    assert claimed.id == running_job.id
    assert claimed.status == JOB_STATUS_RUNNING
    assert claimed.attempt == 2
    assert claimed.locked_by == "w1"


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
    )
    unknown_principal = _principal("nobody@test.com", ["candidate:access"])

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
