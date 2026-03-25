from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_request_scenario_regeneration_enqueues_targeted_job(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-job@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    previous_active = sim.active_scenario_version_id

    (
        updated_sim,
        regenerated,
        scenario_job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
    )

    assert regenerated.status == "generating"
    assert regenerated.version_index == 2
    assert updated_sim.active_scenario_version_id == previous_active
    assert updated_sim.pending_scenario_version_id == regenerated.id
    assert scenario_job.job_type == "scenario_generation"
    assert scenario_job.payload_json["simulationId"] == sim.id
    assert scenario_job.payload_json["scenarioVersionId"] == regenerated.id

    persisted = await async_session.get(Job, scenario_job.id)
    assert persisted is not None
    assert (
        persisted.idempotency_key
        == f"scenario_version:{regenerated.id}:scenario_generation"
    )

    with pytest.raises(ApiError) as duplicate_exc:
        await scenario_service.request_scenario_regeneration(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
        )
    assert duplicate_exc.value.status_code == 409
    assert duplicate_exc.value.error_code == "SCENARIO_REGENERATION_PENDING"
