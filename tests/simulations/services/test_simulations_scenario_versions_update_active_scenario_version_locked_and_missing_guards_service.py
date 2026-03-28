from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_update_active_scenario_version_locked_and_missing_guards(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-update-guards@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "locked"
    await async_session.commit()

    with pytest.raises(ApiError) as locked_exc:
        await scenario_service.update_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
            updates={"focus_notes": "x"},
        )
    assert locked_exc.value.error_code == "SCENARIO_LOCKED"

    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()
    with pytest.raises(ApiError) as missing_exc:
        await scenario_service.update_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
            updates={"focus_notes": "x"},
        )
    assert missing_exc.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"
