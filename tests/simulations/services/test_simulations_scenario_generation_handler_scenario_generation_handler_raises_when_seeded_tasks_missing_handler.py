from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_raises_when_seeded_tasks_missing(
    async_session,
):
    recruiter = await create_recruiter(async_session, email="missing-tasks@test.com")
    sim, tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    for task in tasks:
        await async_session.delete(task)
    await async_session.commit()

    with pytest.raises(RuntimeError, match="scenario_generation_missing_seeded_tasks"):
        await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
