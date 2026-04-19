from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.shared.database.shared_database_models_model import Job, Trial
from app.shared.jobs import worker
from app.shared.jobs.handlers import scenario_generation as scenario_handler
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
)
from tests.shared.factories import create_talent_partner
from tests.trials.routes.trials_scenario_generation_flow_api_utils import (
    create_trial,
    session_maker,
)


@pytest.mark.asyncio
async def test_scenario_generation_failure_marks_job_failed_and_keeps_generating(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setattr(
        scenario_handler, "async_session_maker", session_maker(async_session)
    )
    talent_partner = await create_talent_partner(
        async_session, email="scenario-api-failure@test.com"
    )
    talent_partner_email = talent_partner.email
    created = await create_trial(async_client, auth_header_factory(talent_partner))
    trial_id = created["id"]
    job_id = created["scenarioGenerationJobId"]

    async with session_maker(async_session)() as check_session:
        job = await check_session.get(Job, job_id)
        assert job is not None
        job.max_attempts = 1
        await check_session.commit()

    monkeypatch.setattr(
        scenario_handler,
        "generate_scenario_payload",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("forced scenario generation failure")
        ),
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker(async_session),
            worker_id="scenario-api-failure-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    async with session_maker(async_session)() as check_session:
        refreshed_trial = await check_session.get(Trial, trial_id)
        refreshed_job = await check_session.get(Job, job_id)
    assert refreshed_trial is not None and refreshed_job is not None
    assert refreshed_trial.status == "generating"
    assert refreshed_trial.active_scenario_version_id is None
    assert refreshed_job.status == JOB_STATUS_DEAD_LETTER

    async_session.expire_all()
    job_status_response = await async_client.get(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer talent_partner:{talent_partner_email}"},
    )
    assert job_status_response.status_code == 200, job_status_response.text
    job_status = job_status_response.json()
    assert job_status["jobType"] == "scenario_generation"
    assert job_status["status"] == "failed"
    assert "forced scenario generation failure" in (job_status["error"] or "")

    detail_response = await async_client.get(
        f"/api/trials/{trial_id}",
        headers=auth_header_factory(talent_partner),
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["generationStatus"] == "failed"
    assert detail["generationFailure"] is not None
    assert detail["generationFailure"]["jobId"] == job_id
    assert detail["generationFailure"]["status"] == "failed"
    assert detail["generationFailure"]["retryable"] is True
    assert detail["generationFailure"]["canRetry"] is True
    assert detail["canRetryGeneration"] is True
    assert detail["scenario"] is None

    retry_response = await async_client.post(
        f"/api/trials/{trial_id}/scenario/regenerate",
        headers=auth_header_factory(talent_partner),
    )
    assert retry_response.status_code == 200, retry_response.text
    retry_body = retry_response.json()
    assert retry_body["scenarioVersionId"] is not None
    assert retry_body["jobId"] is not None
    assert retry_body["status"] == "generating"
