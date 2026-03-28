from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_rubric_replace_replaces_non_object_existing(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-patch-rubric-list@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    sim.status = "ready_for_review"
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.rubric_json = []
    await async_session.commit()

    patched = await scenario_service.patch_scenario_version(
        async_session,
        simulation_id=sim.id,
        scenario_version_id=active.id,
        actor_user_id=recruiter.id,
        updates={"rubric_json": {"dayWeights": {"1": 10}}},
    )
    assert patched.rubric_json["dayWeights"]["1"] == 10
