from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_targets_specific_pending_version(
    async_session,
):
    recruiter = await create_recruiter(async_session, email="targeted-version@test.com")
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )

    first = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert first["status"] == "completed"
    active_v1_id = first["scenarioVersionId"]

    pending_v2 = _build_scenario_version(
        sim,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_GENERATING,
        storyline_md="pending",
    )
    async_session.add(pending_v2)
    await async_session.flush()
    sim.pending_scenario_version_id = pending_v2.id
    sim.status = "ready_for_review"
    await async_session.commit()

    targeted = await scenario_handler.handle_scenario_generation(
        {"simulationId": sim.id, "scenarioVersionId": pending_v2.id}
    )
    assert targeted["status"] == "completed"
    assert targeted["scenarioVersionId"] == pending_v2.id

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        refreshed_sim = await check_session.get(Simulation, sim.id)
        refreshed_v2 = await check_session.get(ScenarioVersion, pending_v2.id)
    assert refreshed_sim is not None
    assert refreshed_v2 is not None
    assert refreshed_sim.active_scenario_version_id == active_v1_id
    assert refreshed_sim.pending_scenario_version_id == pending_v2.id
    assert refreshed_sim.status == "ready_for_review"
    assert refreshed_v2.status == SCENARIO_VERSION_STATUS_READY
    assert refreshed_v2.storyline_md
    assert refreshed_v2.task_prompts_json
