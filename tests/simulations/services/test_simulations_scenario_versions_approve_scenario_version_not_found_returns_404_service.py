from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_approve_scenario_version_not_found_returns_404(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-approve-missing@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)

    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.approve_scenario_version(
            async_session,
            simulation_id=sim.id,
            scenario_version_id=999999,
            actor_user_id=recruiter.id,
        )
    assert excinfo.value.status_code == 404
