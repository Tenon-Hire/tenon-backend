from __future__ import annotations

import pytest

from app.shared.database.shared_database_models_model import Company
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_SUCCEEDED,
)
from tests.shared.factories import (
    create_candidate_session,
    create_job,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_get_job_status_talent_partner_owner_returns_shape(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="owner-jobs@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session, trial=sim, invite_email="candidate-jobs@test.com"
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="scenario-owner-1",
        payload_json={"trialId": sim.id},
        company_id=talent_partner.company_id,
        candidate_session_id=cs.id,
        correlation_id="req-123",
    )
    res = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer talent_partner:{talent_partner.email}"},
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
    [(JOB_STATUS_SUCCEEDED, "completed"), (JOB_STATUS_DEAD_LETTER, "failed")],
)
async def test_get_job_status_maps_terminal_status_for_scenario_generation(
    async_client, async_session, stored_status: str, expected_public_status: str
):
    talent_partner = await create_talent_partner(
        async_session, email=f"jobs-status-map-{stored_status}@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=stored_status,
        job_type="scenario_generation",
        payload_json={"trialId": sim.id},
        result_json={"ok": True} if stored_status == JOB_STATUS_SUCCEEDED else None,
    )
    if stored_status == JOB_STATUS_DEAD_LETTER:
        job.last_error = "scenario generation failed"
    await async_session.commit()

    res = await async_client.get(
        f"/api/jobs/{job.id}",
        headers={"Authorization": f"Bearer talent_partner:{talent_partner.email}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["jobType"] == "scenario_generation"
    assert body["status"] == expected_public_status
    assert body["pollAfterMs"] == 0
