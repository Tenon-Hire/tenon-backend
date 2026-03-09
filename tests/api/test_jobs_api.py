from __future__ import annotations

import pytest

from app.domains import Company
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import JOB_STATUS_DEAD_LETTER, JOB_STATUS_SUCCEEDED
from tests.factories import (
    create_candidate_session,
    create_job,
    create_recruiter,
    create_simulation,
)


@pytest.mark.asyncio
async def test_get_job_status_recruiter_owner_returns_shape(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="owner-jobs@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, invite_email="candidate-jobs@test.com"
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="scenario-owner-1",
        payload_json={"simulationId": sim.id},
        company_id=recruiter.company_id,
        candidate_session_id=cs.id,
        correlation_id="req-123",
    )

    res = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer recruiter:{recruiter.email}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == {
        "jobId",
        "jobType",
        "status",
        "attempt",
        "maxAttempts",
        "pollAfterMs",
        "result",
        "error",
    }
    assert body["jobId"] == job.id
    assert body["jobType"] == "scenario_generation"
    assert body["status"] == "queued"
    assert body["attempt"] == 0
    assert body["maxAttempts"] == 5
    assert body["pollAfterMs"] == 1500
    assert body["result"] is None
    assert body["error"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stored_status", "expected_public_status"),
    [
        (JOB_STATUS_SUCCEEDED, "completed"),
        (JOB_STATUS_DEAD_LETTER, "failed"),
    ],
)
async def test_get_job_status_maps_terminal_status_for_scenario_generation(
    async_client,
    async_session,
    stored_status: str,
    expected_public_status: str,
):
    recruiter = await create_recruiter(
        async_session, email=f"jobs-status-map-{stored_status}@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=stored_status,
        job_type="scenario_generation",
        payload_json={"simulationId": sim.id},
        result_json={"ok": True} if stored_status == JOB_STATUS_SUCCEEDED else None,
    )
    if stored_status == JOB_STATUS_DEAD_LETTER:
        job.last_error = "scenario generation failed"
    await async_session.commit()

    res = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer recruiter:{recruiter.email}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["jobType"] == "scenario_generation"
    assert body["status"] == expected_public_status
    assert body["pollAfterMs"] == 0


@pytest.mark.asyncio
async def test_get_job_status_hidden_for_wrong_recruiter(async_client, async_session):
    owner = await create_recruiter(async_session, email="jobs-owner@test.com")
    other = await create_recruiter(async_session, email="jobs-other@test.com")
    sim, _ = await create_simulation(async_session, created_by=owner)
    cs = await create_candidate_session(async_session, simulation=sim)
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="scenario-owner-2",
        payload_json={"simulationId": sim.id},
        company_id=owner.company_id,
        candidate_session_id=cs.id,
    )

    res = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer recruiter:{other.email}"},
    )
    assert res.status_code == 404
    body = res.json()
    assert body["errorCode"] == "JOB_NOT_FOUND"
    assert body["retryable"] is False


@pytest.mark.asyncio
async def test_get_job_status_candidate_ownership(async_client, async_session):
    recruiter = await create_recruiter(
        async_session, email="jobs-candidate-owner@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="candidate-owner@test.com",
    )
    company = await async_session.get(Company, recruiter.company_id)
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
    recruiter = await create_recruiter(
        async_session, email="jobs-candidate-sub-owner@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="candidate-sub-owner@test.com",
        candidate_auth0_sub="candidate-someone-else@test.com",
    )
    company = await async_session.get(Company, recruiter.company_id)
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
    recruiter = await create_recruiter(
        async_session, email="jobs-candidate-company-scope@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="candidate-company-scope@test.com",
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_SUCCEEDED,
        job_type="scenario_generation",
        payload_json={"simulationId": sim.id},
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
