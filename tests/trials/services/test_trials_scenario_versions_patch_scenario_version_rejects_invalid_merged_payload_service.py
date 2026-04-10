from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_rejects_invalid_merged_payload(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-invalid@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    sim.status = "ready_for_review"
    await async_session.commit()
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    original_storyline = active.storyline_md

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=talent_partner.id,
            updates={"task_prompts_json": [{"dayIndex": 99, "description": "x"}]},
        )
    assert excinfo.value.status_code == 422
    assert excinfo.value.error_code == "SCENARIO_PATCH_INVALID"
    invalid_audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit).where(
                    ScenarioEditAudit.scenario_version_id == active.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert invalid_audits == []
    await async_session.refresh(active)
    assert active.storyline_md == original_storyline
