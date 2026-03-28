from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_create_simulation_with_tasks_flow(async_session, monkeypatch):
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "templateKey": "python-fastapi",
        },
    )()
    user = type("U", (), {"company_id": 1, "id": 2})
    sim, tasks, scenario_job = await sim_service.create_simulation_with_tasks(
        async_session, payload, user
    )
    assert sim.id is not None
    assert sim.active_scenario_version_id is None
    assert sim.status == "generating"
    assert scenario_job.job_type == "scenario_generation"
    assert scenario_job.payload_json["simulationId"] == sim.id
    assert len(tasks) == len(sim_service.DEFAULT_5_DAY_BLUEPRINT)
    # ensure tasks are sorted and refreshed
    assert tasks[0].day_index == 1
