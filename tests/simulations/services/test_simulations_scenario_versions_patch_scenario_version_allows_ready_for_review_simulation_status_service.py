from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_allows_ready_for_review_simulation_status(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-patch-ready-for-review-status@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    sim.status = "ready_for_review"
    await async_session.commit()
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    assert active.status == "ready"

    patched = await scenario_service.patch_scenario_version(
        async_session,
        simulation_id=sim.id,
        scenario_version_id=active.id,
        actor_user_id=recruiter.id,
        updates={"focus_notes": "Edited in ready_for_review simulation state"},
    )
    assert patched.focus_notes == "Edited in ready_for_review simulation state"
