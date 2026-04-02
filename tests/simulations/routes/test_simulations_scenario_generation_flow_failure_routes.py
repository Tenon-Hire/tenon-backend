from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.shared.database.shared_database_models_model import Job, Simulation
from app.shared.jobs import worker
from app.shared.jobs.handlers import scenario_generation as scenario_handler
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
)
from tests.shared.factories import create_recruiter
from tests.simulations.routes.simulations_scenario_generation_flow_api_utils import (
    create_simulation,
    session_maker,
)


@pytest.mark.asyncio
async def test_scenario_generation_failure_marks_job_failed_and_keeps_generating(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setattr(
        scenario_handler, "async_session_maker", session_maker(async_session)
    )
    recruiter = await create_recruiter(
        async_session, email="scenario-api-failure@test.com"
    )
    recruiter_email = recruiter.email
    created = await create_simulation(async_client, auth_header_factory(recruiter))
    simulation_id = created["id"]
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
        refreshed_simulation = await check_session.get(Simulation, simulation_id)
        refreshed_job = await check_session.get(Job, job_id)
    assert refreshed_simulation is not None and refreshed_job is not None
    assert refreshed_simulation.status == "generating"
    assert refreshed_simulation.active_scenario_version_id is None
    assert refreshed_job.status == JOB_STATUS_DEAD_LETTER

    async_session.expire_all()
    job_status_response = await async_client.get(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer recruiter:{recruiter_email}"},
    )
    assert job_status_response.status_code == 200, job_status_response.text
    job_status = job_status_response.json()
    assert job_status["jobType"] == "scenario_generation"
    assert job_status["status"] == "failed"
    assert "forced scenario generation failure" in (job_status["error"] or "")
