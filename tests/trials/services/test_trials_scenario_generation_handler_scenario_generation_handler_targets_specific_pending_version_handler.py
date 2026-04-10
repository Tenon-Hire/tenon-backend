from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_targets_specific_pending_version(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="targeted-version@test.com"
    )
    sim, _tasks, _job = await create_trial_with_tasks(
        async_session,
        _trial_payload(),
        talent_partner,
    )

    first = await scenario_handler.handle_scenario_generation({"trialId": sim.id})
    assert first["status"] == "completed"
    active_v1_id = first["scenarioVersionId"]

    pending_v2 = _build_scenario_version(
        sim,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_GENERATING,
        storyline_md="pending",
    )
    async_session.add(pending_v2)
    await async_session.flush()
    sim.pending_scenario_version_id = pending_v2.id
    sim.status = "ready_for_review"
    await async_session.commit()

    targeted = await scenario_handler.handle_scenario_generation(
        {"trialId": sim.id, "scenarioVersionId": pending_v2.id}
    )
    assert targeted["status"] == "completed"
    assert targeted["scenarioVersionId"] == pending_v2.id

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        refreshed_sim = await check_session.get(Trial, sim.id)
        refreshed_v2 = await check_session.get(ScenarioVersion, pending_v2.id)
    assert refreshed_sim is not None
    assert refreshed_v2 is not None
    assert refreshed_sim.active_scenario_version_id == active_v1_id
    assert refreshed_sim.pending_scenario_version_id == pending_v2.id
    assert refreshed_sim.status == "ready_for_review"
    assert refreshed_v2.status == SCENARIO_VERSION_STATUS_READY
    assert refreshed_v2.storyline_md
    assert refreshed_v2.task_prompts_json
