from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_target_version_guard_paths(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="target-guard-paths@test.com"
    )
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )

    locked_v2 = _build_scenario_version(
        sim,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_LOCKED,
        storyline_md="locked",
    )
    async_session.add(locked_v2)
    await async_session.commit()

    locked_result = await scenario_handler.handle_scenario_generation(
        {"simulationId": sim.id, "scenarioVersionId": locked_v2.id}
    )
    assert locked_result == {
        "status": "skipped_locked_scenario_version",
        "simulationId": sim.id,
        "scenarioVersionId": locked_v2.id,
    }

    missing_result = await scenario_handler.handle_scenario_generation(
        {"simulationId": sim.id, "scenarioVersionId": 999999}
    )
    assert missing_result == {
        "status": "scenario_version_not_found",
        "simulationId": sim.id,
        "scenarioVersionId": 999999,
    }
