from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_is_idempotent_for_locked(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-lock-idempotent@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "locked"
    active.locked_at = datetime.now(UTC)
    await async_session.commit()

    locked = await scenario_service.lock_active_scenario_for_invites(
        async_session, simulation_id=sim.id
    )
    assert locked.id == active.id
    assert locked.status == "locked"
