from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_uses_from_scratch_key(async_session):
    payload = type(
        "Payload",
        (),
        {
            "title": "t",
            "role": "r",
            "preferredLanguageFramework": "ts",
            "seniority": "s",
            "focus": "f",
        },
    )()
    sim, _tasks, _job = await trial_service.create_trial_with_tasks(
        async_session, payload, SimpleNamespace(id=1, company_id=1)
    )
    assert sim.template_key == "from-scratch"
