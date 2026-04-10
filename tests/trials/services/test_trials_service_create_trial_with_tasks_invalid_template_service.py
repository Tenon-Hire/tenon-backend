from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_invalid_template():
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
    with pytest.raises(sim_service.ApiError):
        await sim_service.create_trial_with_tasks(
            None, payload, SimpleNamespace(id=1, company_id=1)
        )
