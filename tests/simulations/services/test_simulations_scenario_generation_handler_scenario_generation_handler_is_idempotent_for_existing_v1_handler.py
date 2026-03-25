from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_is_idempotent_for_existing_v1(async_session):
    recruiter = await create_recruiter(
        async_session, email="idempotent-scenario@test.com"
    )
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )

    first = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    second = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert first["status"] == "completed"
    assert second["status"] == "completed"

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        versions = (
            (
                await check_session.execute(
                    select(ScenarioVersion)
                    .where(ScenarioVersion.simulation_id == sim.id)
                    .order_by(ScenarioVersion.version_index.asc())
                )
            )
            .scalars()
            .all()
        )
        refreshed_sim = await check_session.get(Simulation, sim.id)
    assert len(versions) == 1
    assert versions[0].version_index == 1
    assert refreshed_sim is not None
    assert refreshed_sim.status == "ready_for_review"
    assert refreshed_sim.active_scenario_version_id == versions[0].id
