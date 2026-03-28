from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_create_simulation_with_tasks_logs_ai_config_changes_without_notice_text(
    async_session,
    caplog,
):
    recruiter = await create_recruiter(async_session, email="sim-log@test.com")
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "ai": {
                "noticeVersion": "mvp2",
                "noticeText": "Private AI notice text should not be logged.",
                "evalEnabledByDay": {"1": True, "2": False},
            },
            "templateKey": "python-fastapi",
        },
    )()

    caplog.set_level(
        "INFO",
        logger="app.simulations.services.simulations_services_simulations_creation_service",
    )
    sim, tasks, _scenario_job = await sim_service.create_simulation_with_tasks(
        async_session,
        payload,
        recruiter,
    )

    assert sim.id is not None
    assert len(tasks) == len(sim_service.DEFAULT_5_DAY_BLUEPRINT)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert (
        f"simulation_ai_notice_version_changed simulationId={sim.id} "
        f"actorUserId={recruiter.id} from=mvp1 to=mvp2"
    ) in log_text
    assert (
        f"simulation_ai_eval_toggles_changed simulationId={sim.id} "
        f"actorUserId={recruiter.id} changedDays=[2]"
    ) in log_text
    assert "Private AI notice text should not be logged." not in log_text
