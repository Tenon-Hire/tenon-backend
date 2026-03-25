from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_list_with_candidate_counts(async_session):
    recruiter = await create_recruiter(async_session, email="counts@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    rows = await sim_service.list_simulations(async_session, recruiter.id)
    assert rows[0][0].id == sim.id
