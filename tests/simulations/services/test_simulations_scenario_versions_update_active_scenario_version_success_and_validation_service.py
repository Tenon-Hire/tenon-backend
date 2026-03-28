from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_update_active_scenario_version_success_and_validation(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-update-success@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)

    updated = await scenario_service.update_active_scenario_version(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
        updates={
            "storyline_md": "## Updated",
            "task_prompts_json": [{"dayIndex": 1}],
            "rubric_json": {"summary": "rubric"},
            "focus_notes": "Updated focus",
            "status": "draft",
        },
    )
    assert updated.storyline_md == "## Updated"
    assert updated.task_prompts_json == [{"dayIndex": 1}]
    assert updated.rubric_json == {"summary": "rubric"}
    assert updated.focus_notes == "Updated focus"
    assert updated.status == "draft"

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.update_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
            updates={"status": "invalid"},
        )
    assert excinfo.value.status_code == 422
    assert excinfo.value.error_code == "SCENARIO_STATUS_INVALID"
