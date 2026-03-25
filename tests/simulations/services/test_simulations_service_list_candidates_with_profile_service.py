from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_list_candidates_with_profile(async_session):
    recruiter = await create_recruiter(async_session, email="list@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs, _created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=type("P", (), {"candidateName": "a", "inviteEmail": "b@example.com"}),
        scenario_version_id=sim.active_scenario_version_id,
    )
    rows = await sim_service.list_candidates_with_profile(async_session, sim.id)
    assert rows and rows[0][0].id == cs.id
