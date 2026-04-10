from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_rubric_replace_replaces_non_object_existing(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-rubric-list@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    sim.status = "ready_for_review"
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.rubric_json = []
    await async_session.commit()

    patched = await scenario_service.patch_scenario_version(
        async_session,
        trial_id=sim.id,
        scenario_version_id=active.id,
        actor_user_id=talent_partner.id,
        updates={"rubric_json": {"dayWeights": {"1": 10}}},
    )
    assert patched.rubric_json["dayWeights"]["1"] == 10
