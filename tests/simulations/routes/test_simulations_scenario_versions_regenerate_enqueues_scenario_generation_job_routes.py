from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_enqueues_scenario_generation_job(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="scenario-job-queue@test.com"
    )
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )
    headers = auth_header_factory(recruiter)
    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    regenerate = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert regenerate.status_code == 200, regenerate.text
    payload = regenerate.json()

    job = await async_session.get(Job, payload["jobId"])
    assert job is not None
    assert job.status == JOB_STATUS_QUEUED
    assert job.payload_json["simulationId"] == sim_id
    assert job.payload_json["scenarioVersionId"] == payload["scenarioVersionId"]
