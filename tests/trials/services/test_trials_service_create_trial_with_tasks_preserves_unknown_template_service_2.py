from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_preserves_unknown_template(async_session):
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "templateKey": "not-real",
        },
    )()
    user = type("U", (), {"company_id": 1, "id": 2})
    sim, _tasks, _job = await sim_service.create_trial_with_tasks(
        async_session, payload, user
    )
    assert sim.template_key == "not-real"
