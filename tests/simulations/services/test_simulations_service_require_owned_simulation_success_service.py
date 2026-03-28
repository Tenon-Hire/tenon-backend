from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_require_owned_simulation_success(async_session):
    recruiter = await create_recruiter(async_session, email="owned@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    owned = await sim_service.require_owned_simulation(
        async_session, sim.id, recruiter.id
    )
    assert owned.id == sim.id
