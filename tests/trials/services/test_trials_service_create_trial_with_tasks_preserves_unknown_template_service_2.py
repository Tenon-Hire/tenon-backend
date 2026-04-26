from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_uses_from_scratch_key(async_session):
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "preferredLanguageFramework": "Python",
            "seniority": "Mid",
            "focus": "Build",
        },
    )()
    user = type("U", (), {"company_id": 1, "id": 2})
    sim, _tasks, _job = await trial_service.create_trial_with_tasks(
        async_session, payload, user
    )
    assert sim.template_key == "from-scratch"
