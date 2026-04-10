from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_rejects_bad_template(async_session):
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
    with pytest.raises(Exception) as excinfo:
        await sim_service.create_trial_with_tasks(async_session, payload, user)
    assert excinfo.value.status_code == 422
    assert getattr(excinfo.value, "error_code", None) == "INVALID_TEMPLATE_KEY"
    assert "Invalid templateKey" in str(excinfo.value.detail)
