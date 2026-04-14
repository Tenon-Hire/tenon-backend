from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_approve_scenario_version_without_pending_state_branches(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-approve-nopending@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    active_id = sim.active_scenario_version_id
    assert active_id is not None

    sim.status = "ready_for_review"
    await async_session.flush()

    approved_sim, approved_version = await scenario_service.approve_scenario_version(
        async_session,
        trial_id=sim.id,
        scenario_version_id=active_id,
        actor_user_id=talent_partner.id,
    )
    assert approved_sim.status == "ready_for_review"
    assert approved_version.id == active_id
    assert approved_version.locked_at is not None

    non_active = ScenarioVersion(
        trial_id=sim.id,
        version_index=2,
        status="ready",
        storyline_md="# v2",
        task_prompts_json=[],
        rubric_json={},
        focus_notes=sim.focus,
        template_key=sim.template_key,
        tech_stack=sim.tech_stack,
        seniority=sim.seniority,
    )
    async_session.add(non_active)
    await async_session.commit()

    with pytest.raises(ApiError) as not_pending_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=non_active.id,
            actor_user_id=talent_partner.id,
        )
    assert not_pending_exc.value.status_code == 409
    assert not_pending_exc.value.error_code == "SCENARIO_APPROVAL_NOT_PENDING"
