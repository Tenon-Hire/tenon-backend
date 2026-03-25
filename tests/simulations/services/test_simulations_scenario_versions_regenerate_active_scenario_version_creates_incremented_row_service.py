from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_regenerate_active_scenario_version_creates_incremented_row(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-ok@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)

    previous_active = sim.active_scenario_version_id
    (
        updated_sim,
        regenerated,
    ) = await scenario_service.regenerate_active_scenario_version(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
    )

    assert regenerated.version_index == 2
    assert regenerated.id != previous_active
    assert regenerated.status == "generating"
    assert updated_sim.active_scenario_version_id == previous_active
    assert updated_sim.pending_scenario_version_id == regenerated.id
    assert updated_sim.status == "ready_for_review"

    versions = (
        (
            await async_session.execute(
                select(ScenarioVersion)
                .where(ScenarioVersion.simulation_id == sim.id)
                .order_by(ScenarioVersion.version_index.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [version.version_index for version in versions] == [1, 2]
    assert versions[0].id == previous_active
    assert versions[1].id == regenerated.id
