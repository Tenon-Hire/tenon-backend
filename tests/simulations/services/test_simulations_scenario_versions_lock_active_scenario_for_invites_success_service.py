from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_success(async_session):
    recruiter = await create_recruiter(async_session, email="scenario-lock-ok@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    now = datetime.now(UTC).replace(microsecond=0)

    locked = await scenario_service.lock_active_scenario_for_invites(
        async_session, simulation_id=sim.id, now=now
    )

    assert locked.status == "locked"
    assert locked.locked_at == now
