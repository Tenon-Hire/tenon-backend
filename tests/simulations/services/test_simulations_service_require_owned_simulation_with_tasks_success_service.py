from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_require_owned_simulation_with_tasks_success(async_session):
    recruiter = await create_recruiter(async_session, email="owned@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    found_sim, found_tasks = await sim_service.require_owned_simulation_with_tasks(
        async_session, sim.id, recruiter.id
    )
    assert found_sim.id == sim.id
    assert [t.id for t in found_tasks] == [t.id for t in tasks]
