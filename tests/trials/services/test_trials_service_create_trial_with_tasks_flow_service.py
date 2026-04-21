from __future__ import annotations

import pytest

from app.shared.utils.shared_utils_errors_utils import ApiError
from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_flow(async_session, monkeypatch):
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
    sim, tasks, scenario_job = await sim_service.create_trial_with_tasks(
        async_session, payload, user
    )
    assert sim.id is not None
    assert sim.active_scenario_version_id is None
    assert sim.status == "generating"
    assert sim.day_window_overrides_enabled is True
    assert sim.day_window_overrides_json == {
        "5": {"startLocal": "09:00", "endLocal": "21:00"}
    }
    assert scenario_job.job_type == "scenario_generation"
    assert scenario_job.payload_json["trialId"] == sim.id
    assert len(tasks) == len(sim_service.DEFAULT_5_DAY_BLUEPRINT)
    # ensure tasks are sorted and refreshed
    assert tasks[0].day_index == 1
    assert tasks[-1].type == "reflection"


def test_build_trial_for_create_rejects_conflicting_day5_override():
    payload = SimpleNamespace(
        title="Title",
        role="Role",
        techStack="Python",
        seniority="Mid",
        focus="Build",
        templateKey="python-fastapi",
        dayWindowOverridesEnabled=True,
        dayWindowOverrides={
            "5": {"startLocal": "10:00", "endLocal": "18:00"},
        },
    )
    user = SimpleNamespace(company_id=1, id=2)

    with pytest.raises(ApiError) as excinfo:
        sim_creation.build_trial_for_create(payload, user)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error_code == "TRIAL_DAY5_WINDOW_OVERRIDE_INVALID"
    assert excinfo.value.details["field"] == "dayWindowOverrides.5"
