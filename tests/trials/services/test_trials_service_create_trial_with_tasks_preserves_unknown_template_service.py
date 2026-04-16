from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_preserves_unknown_template(async_session):
    payload = type(
        "Payload",
        (),
        {
            "title": "t",
            "role": "r",
            "techStack": "ts",
            "seniority": "s",
            "focus": "f",
            "templateKey": "invalid-key",
        },
    )()
    sim, _tasks, _job = await sim_service.create_trial_with_tasks(
        async_session, payload, SimpleNamespace(id=1, company_id=1)
    )
    assert sim.template_key == "invalid-key"
