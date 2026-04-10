from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_raises_when_seeded_tasks_missing(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="missing-tasks@test.com"
    )
    sim, tasks, _job = await create_trial_with_tasks(
        async_session,
        _trial_payload(),
        talent_partner,
    )
    for task in tasks:
        await async_session.delete(task)
    await async_session.commit()

    with pytest.raises(RuntimeError, match="scenario_generation_missing_seeded_tasks"):
        await scenario_handler.handle_scenario_generation({"trialId": sim.id})
