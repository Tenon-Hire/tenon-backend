from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_skips_unexpected_status(async_session):
    recruiter = await create_recruiter(
        async_session, email="unexpected-status-sim@test.com"
    )
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    sim.status = "draft"
    await async_session.commit()

    result = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert result == {
        "status": "skipped_unexpected_status",
        "simulationId": sim.id,
        "simulationStatus": "draft",
    }
