from __future__ import annotations

import pytest

from app.shared.database.shared_database_models_model import Job, Simulation
from app.shared.jobs.handlers import scenario_generation as scenario_handler
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
)
from tests.shared.factories import create_recruiter
from tests.simulations.routes.simulations_scenario_generation_flow_api_utils import (
    create_simulation,
    session_maker,
)


@pytest.mark.asyncio
async def test_create_simulation_returns_generating_and_scenario_job_id(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setattr(
        scenario_handler, "async_session_maker", session_maker(async_session)
    )
    recruiter = await create_recruiter(
        async_session, email="scenario-api-create@test.com"
    )
    created = await create_simulation(async_client, auth_header_factory(recruiter))
    assert created["status"] == "generating"
    assert created["scenarioGenerationJobId"]

    simulation = await async_session.get(Simulation, created["id"])
    assert simulation is not None
    assert simulation.status == "generating"
    assert simulation.active_scenario_version_id is None
    job = await async_session.get(Job, created["scenarioGenerationJobId"])
    assert job is not None
    assert job.job_type == "scenario_generation"
    assert job.status == JOB_STATUS_QUEUED
    assert job.payload_json["simulationId"] == created["id"]
