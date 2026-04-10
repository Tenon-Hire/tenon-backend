from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_logs_ai_config_changes_without_notice_text(
    async_session,
    caplog,
):
    talent_partner = await create_talent_partner(
        async_session, email="sim-log@test.com"
    )
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
        logger="app.trials.services.trials_services_trials_creation_service",
    )
    sim, tasks, _scenario_job = await sim_service.create_trial_with_tasks(
        async_session,
        payload,
        talent_partner,
    )

    assert sim.id is not None
    assert len(tasks) == len(sim_service.DEFAULT_5_DAY_BLUEPRINT)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert (
        f"trial_ai_notice_version_changed trialId={sim.id} "
        f"actorUserId={talent_partner.id} from=mvp1 to=mvp2"
    ) in log_text
    assert (
        f"trial_ai_eval_toggles_changed trialId={sim.id} "
        f"actorUserId={talent_partner.id} changedDays=[2]"
    ) in log_text
    assert "Private AI notice text should not be logged." not in log_text
