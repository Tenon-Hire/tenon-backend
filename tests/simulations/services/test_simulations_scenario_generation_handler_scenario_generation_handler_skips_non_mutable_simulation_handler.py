from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_skips_non_mutable_simulation(async_session):
    recruiter = await create_recruiter(async_session, email="non-mutable-sim@test.com")
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    completed = await scenario_handler.handle_scenario_generation(
        {"simulationId": sim.id}
    )
    assert completed["status"] == "completed"
    sim.status = "terminated"
    await async_session.commit()

    result = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert result == {
        "status": "skipped_non_mutable_simulation",
        "simulationId": sim.id,
        "simulationStatus": "terminated",
    }
