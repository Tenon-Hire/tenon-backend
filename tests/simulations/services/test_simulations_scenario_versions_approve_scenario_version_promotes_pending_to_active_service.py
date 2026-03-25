from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_approve_scenario_version_promotes_pending_to_active(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-approve-ok@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    previous_active = sim.active_scenario_version_id
    (
        _updated_sim,
        regenerated,
        _job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
    )
    regenerated.status = "ready"
    await async_session.commit()

    approved_sim, approved_version = await scenario_service.approve_scenario_version(
        async_session,
        simulation_id=sim.id,
        scenario_version_id=regenerated.id,
        actor_user_id=recruiter.id,
    )

    assert approved_version.id == regenerated.id
    assert approved_sim.pending_scenario_version_id is None
    assert approved_sim.active_scenario_version_id == regenerated.id
    assert approved_sim.active_scenario_version_id != previous_active
    assert approved_sim.status == "active_inviting"

    first_session_active = await async_session.get(ScenarioVersion, previous_active)
    assert first_session_active is not None
