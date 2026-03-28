from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_create_initial_scenario_version_sets_active_and_payload(async_session):
    recruiter = await create_recruiter(async_session, email="scenario-init@test.com")
    sim, tasks = await _create_bare_simulation(async_session, recruiter)

    scenario = await scenario_service.create_initial_scenario_version(
        async_session, simulation=sim, tasks=tasks
    )

    assert scenario.version_index == 1
    assert scenario.status == "ready"
    assert sim.active_scenario_version_id == scenario.id
    assert scenario.task_prompts_json[0]["dayIndex"] == 1
    assert scenario.task_prompts_json[1]["dayIndex"] == 2
