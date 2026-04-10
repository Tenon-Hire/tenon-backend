from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_skips_non_mutable_trial(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="non-mutable-sim@test.com"
    )
    sim, _tasks, _job = await create_trial_with_tasks(
        async_session,
        _trial_payload(),
        talent_partner,
    )
    completed = await scenario_handler.handle_scenario_generation({"trialId": sim.id})
    assert completed["status"] == "completed"
    sim.status = "terminated"
    await async_session.commit()

    result = await scenario_handler.handle_scenario_generation({"trialId": sim.id})
    assert result == {
        "status": "skipped_non_mutable_trial",
        "trialId": sim.id,
        "trialStatus": "terminated",
    }
