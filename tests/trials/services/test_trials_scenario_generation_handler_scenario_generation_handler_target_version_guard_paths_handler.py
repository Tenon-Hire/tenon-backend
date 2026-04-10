from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_target_version_guard_paths(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="target-guard-paths@test.com"
    )
    sim, _tasks, _job = await create_trial_with_tasks(
        async_session,
        _trial_payload(),
        talent_partner,
    )

    locked_v2 = _build_scenario_version(
        sim,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_LOCKED,
        storyline_md="locked",
    )
    async_session.add(locked_v2)
    await async_session.commit()

    locked_result = await scenario_handler.handle_scenario_generation(
        {"trialId": sim.id, "scenarioVersionId": locked_v2.id}
    )
    assert locked_result == {
        "status": "skipped_locked_scenario_version",
        "trialId": sim.id,
        "scenarioVersionId": locked_v2.id,
    }

    missing_result = await scenario_handler.handle_scenario_generation(
        {"trialId": sim.id, "scenarioVersionId": 999999}
    )
    assert missing_result == {
        "status": "scenario_version_not_found",
        "trialId": sim.id,
        "scenarioVersionId": 999999,
    }
